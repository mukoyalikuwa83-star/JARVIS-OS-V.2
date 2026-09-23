"""
Jarvis OS SyncStore — Part 2.9 cross-device memory/audit client contract.

Requirements covered today (single-device, M3-ready):
  2.9.1  One shared memory + audit log across devices  -> SyncStore is the
         client contract. Fully local now (same .jarvis/memory.json as
         core.service_api); remote_configure() is the M3 hook.
  2.9.2  Cross-device handoff  -> every document carries a revision; a handoff
         is just "read rev on device A, write on device B with that expected
         rev". Divergent writers are caught by the rev check.
  2.9.3  Conflicts flagged, never silently dropped  -> a stale write is NEVER
         applied silently: the incoming document is preserved in-place under a
         quarantine key (_conflicts.<key>.<rev>) AND recorded in the append-only
         .jarvis/conflicts.jsonl. Explicit resolve_conflict() picks the winner.

Storage shape matches core.service_api.memory_write so the whole Core reads one
logical map:  {key: {"value":..., "writer":..., "revision":<sha1-12>,
                       "updated_utc": <iso>}}
"""
import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

STORE_PATH = Path(__file__).resolve().parent.parent / ".jarvis" / "memory.json"
CONFLICT_PATH = Path(__file__).resolve().parent.parent / ".jarvis" / "conflicts.jsonl"
_REMOTE = {"endpoint": None, "configured_at": None}

_lock = threading.Lock()


def _ensure():
    STORE_PATH.parent.mkdir(exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text("{}", encoding="utf-8")


def _read_store() -> Dict:
    _ensure()
    with _lock:
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}


def _write_store(data: Dict):
    _ensure()
    with _lock:
        tmp = STORE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(STORE_PATH)


def _rev(value, writer) -> str:
    return hashlib.sha1(json.dumps([value, writer], sort_keys=True, default=str).encode()).hexdigest()[:12]


def _doc(value, writer) -> Dict:
    return {"value": value, "writer": writer, "revision": _rev(value, writer),
            "updated_utc": datetime.now(timezone.utc).isoformat()}


def _append_conflict(record: Dict):
    CONFLICT_PATH.parent.mkdir(exist_ok=True)
    with CONFLICT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def store_read(key: str) -> Dict:
    """Read one document from the single shared store."""
    data = _read_store()
    if key not in data:
        return {"ok": True, "found": False, "key": key}
    d = data[key]
    return {"ok": True, "found": True, "key": key, "value": d["value"],
            "rev": d["revision"], "writer": d["writer"], "updated_utc": d["updated_utc"]}


def store_write(key: str, value: Any, writer: str = "core",
                expected_rev: Optional[str] = None) -> Dict:
    """Conflict-shaped write. Pass expected_rev to require lineage continuity.

    - If the key exists and expected_rev does not match the current revision,
      the write is REJECTED (never silently applied), the incoming document is
      preserved under _conflicts.<key>.<rev>, and the conflict is logged.
    - Otherwise the document is written with a new revision.
    """
    data = _read_store()
    cur = data.get(key)
    if cur is not None and expected_rev is not None and cur.get("revision") != expected_rev:
        incoming = _doc(value, writer)
        quarantine_key = f"_conflicts.{key}.{incoming['revision']}"
        data[quarantine_key] = incoming
        _write_store(data)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "key": key, "status": "unresolved",
            "incoming_writer": writer, "incoming_rev": incoming["revision"],
            "incoming_value": value if isinstance(value, (str, float, int, bool)) or value is None else json.dumps(value, default=str)[:2000],
            "current_writer": cur.get("writer"), "current_rev": cur.get("revision"),
            "current_value": cur.get("value") if isinstance(cur.get("value"), (str, float, int, bool)) or cur.get("value") is None else json.dumps(cur.get("value"), default=str)[:2000],
            "quarantined_under": quarantine_key,
            "resolved": False,
        }
        _append_conflict(record)
        return {"ok": False, "conflict": True, "key": key,
                "expected_rev": expected_rev, "current_rev": cur.get("revision"),
                "quarantined_under": quarantine_key, "recorded": True}

    doc = _doc(value, writer)
    data[key] = doc
    _write_store(data)
    return {"ok": True, "key": key, "rev": doc["revision"], "writer": writer,
            "conflict": False}


def store_delete(key: str, expected_rev: Optional[str] = None) -> Dict:
    """Delete a document; same rev guard applies (deletions must not be stale)."""
    data = _read_store()
    cur = data.get(key)
    if cur is not None and cur.get("revision") not in (None, expected_rev):
        record = {"ts": datetime.now(timezone.utc).isoformat(), "key": key,
                  "status": "unresolved", "op": "delete", "resolved": False,
                  "current_rev": cur.get("revision"), "expected_rev": expected_rev,
                  "note": "stale delete: current doc retained"}
        _append_conflict(record)
        return {"ok": False, "conflict": True, "key": key}
    if cur is not None:
        data.pop(key, None)
        _write_store(data)
    return {"ok": True, "key": key, "deleted": cur is not None}


def store_list() -> Dict:
    """All live (non-quarantine) keys with revision + writer."""
    data = _read_store()
    live = {k: {"rev": v.get("revision"), "writer": v.get("writer"),
                "updated_utc": v.get("updated_utc")}
            for k, v in data.items() if not k.startswith("_conflicts.")}
    return {"ok": True, "count": len(live), "keys": live}


def list_conflicts(limit: int = 50) -> List[Dict]:
    """Append-only conflict ledger (2.9.3: flagged, never silently dropped)."""
    if not CONFLICT_PATH.exists():
        return []
    out = []
    with CONFLICT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out[-limit:]


def resolve_conflict(key: str, keep: str = "current", writer: str = "operator") -> Dict:
    """Explicit resolution. 'current' = what is live now; 'their' = the
    quarantined incoming document. Both sides were preserved; this picks one.
    """
    if keep not in ("current", "their"):
        return {"ok": False, "error": "keep must be 'current' or 'their'"}
    data = _read_store()
    live = data.get(key)
    quarantined = [k for k in data if k.startswith(f"_conflicts.{key}.")]
    if not quarantined:
        return {"ok": False, "error": "no quarantined conflict for key"}
    chosen = quarantined[0]
    q_doc = data[chosen]

    if keep == "their":
        doc = {"value": q_doc["value"], "writer": q_doc["writer"],
               "revision": _rev(q_doc["value"], q_doc["writer"]),
               "updated_utc": datetime.now(timezone.utc).isoformat(),
               "resolved_from": chosen}
        data[key] = doc
    data.pop(chosen, None)
    _write_store(data)

    live_rev = live.get("revision") if live else None
    queried_rev = q_doc.get("revision")
    _mark_conflict_resolved(key, f"{keep} kept; live before={live_rev}; queried={queried_rev}", writer)

    return {"ok": True, "key": key, "kept": keep, "value": data[key]["value"],
            "rev": data[key]["revision"]}


def _mark_conflict_resolved(key: str, resolution: str, writer: str):
    entries = []
    for rec in list_conflicts(limit=10_000):
        if rec.get("key") == key and rec.get("status") == "unresolved":
            rec["status"] = "resolved"
            rec["resolved"] = True
            rec["resolution"] = resolution
            rec["resolved_by"] = writer
        entries.append(rec)
    with CONFLICT_PATH.open("w", encoding="utf-8") as f:
        for rec in entries:
            f.write(json.dumps(rec) + "\n")


def remote_configure(endpoint: Optional[str]) -> Dict:
    """M3 hook: point this client at the shared remote store."""
    _REMOTE["endpoint"] = endpoint
    _REMOTE["configured_at"] = datetime.now(timezone.utc).isoformat() if endpoint else None
    return {"ok": True, "mode": "local" if not endpoint else "remote",
            "endpoint": endpoint}


def remote_status() -> Dict:
    return {"ok": True, "mode": "local" if not _REMOTE["endpoint"] else "remote",
            "endpoint": _REMOTE["endpoint"], "store_path": str(STORE_PATH),
            "conflict_path": str(CONFLICT_PATH),
            "local_only": _REMOTE["endpoint"] is None}


def handoff(key: str, value: Any) -> Dict:
    """2.9.2 cross-device handoff helper: write, returning the rev another
    device must pass as expected_rev to continue the lineage."""
    r = store_write(key, value, writer="handoff_creator")
    return {"ok": r["ok"], "key": key, "rev": r.get("rev")}


def continue_handoff(key: str, value: Any, expected_rev: str) -> Dict:
    """2.9.2 continuation on another (logical) device using the carried rev."""
    return store_write(key, value, writer="handoff_second_device",
                       expected_rev=expected_rev)


# ---------------------------------------------------------------------------
# Object provider for core.service_api registration (object dispatch branch)
# ---------------------------------------------------------------------------
class SyncStore:
    def read(self, key: str = ""):
        if key:
            return store_read(key)
        return store_list()

    def write(self, key: str, value: Any, writer: str = "core", expected_rev=None):
        return store_write(key, value, writer, expected_rev)

    def conflicts(self, limit: int = 50):
        return {"ok": True, "count": len(list_conflicts(limit)), "entries": list_conflicts(limit)}

    def resolve(self, key: str, keep: str = "current", writer: str = "operator"):
        return resolve_conflict(key, keep, writer)

    def remote(self):
        return remote_status()

    def status(self):
        return store_list()


def _register_with_core():
    try:
        from core.service_api import register_service
        register_service("syncstore", "0.1", [], SyncStore())
    except Exception:
        pass


_register_with_core()
"""
Jarvis OS Core Services — Part 2.8 / Table 2.1 stable internal API.

Every v1.0 domain that becomes an OS-level service is exposed here behind a
typed call contract. Callers (shell, first-party tools, future trusted apps)
invoke services through `invoke_service` — which routes through the
Permission Broker (core.permission_broker) for any sensitive capability, so a
caller can never reach a capability more permissively than a domain agent could.

Services map 1:1 to the v1.0 domain table (Part 2.8 Table 2.1):
    computer_control | phone_messaging | smart_home | money_engine |
    information_news | tracking_monitor | safety_guardian | memory_audit |
    orchestrator
"""
import json
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

from core.audit_log import read_audit_log, get_audit_stats, verify_log_integrity
from core.permission_broker import request_permission, broker_status, SENSITIVE_CAPABILITIES

# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------
_SERVICES: Dict[str, Dict] = {}


def register_service(name: str, version: str, caps: List[str], handler: Callable):
    """Register an OS service with its required capabilities (checked on call)."""
    _SERVICES[name] = {
        "name": name,
        "version": version,
        "capabilities": caps,
        "handler": handler,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


def list_services() -> Dict:
    """Stable introspection: what the Core exposes (Part 2.8 'stable API')."""
    return {n: {"version": s["version"], "capabilities": s["capabilities"]}
            for n, s in _SERVICES.items()}


# ---------------------------------------------------------------------------
# Memory service (2.9: single shared memory across devices)
# ---------------------------------------------------------------------------
_MEM_PATH = None
_mem_lock = None


def _ensure_memory():
    global _MEM_PATH, _mem_lock
    if _MEM_PATH is None:
        import threading
        from pathlib import Path
        _MEM_PATH = Path(__file__).resolve().parent.parent / ".jarvis" / "memory.json"
        _MEM_PATH.parent.mkdir(exist_ok=True)
        if not _MEM_PATH.exists():
            _MEM_PATH.write_text("{}", encoding="utf-8")
        _mem_lock = threading.Lock()
    return _MEM_PATH


def _memory_read() -> Dict:
    _ensure_memory()
    with _mem_lock:
        try:
            return json.loads(_MEM_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}


def _memory_write(data: Dict):
    _ensure_memory()
    with _mem_lock:
        tmp = _MEM_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(_MEM_PATH)


def _couchdoc(data: Dict, key: str) -> Dict:
    return {"_id": key, "_rev": hashlib_sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]}


def hashlib_sha1(b: bytes):
    import hashlib
    return hashlib.sha1(b)


def memory_read(key: str = "", **_kw) -> Dict:
    data = _memory_read()
    if key:
        return {"key": key, "found": key in data, "value": data.get(key)}
    return {"keys": list(data.keys()), "count": len(data), "data": data}


def memory_write(key: str, value: Any, writer: str = "core", **_kw) -> Dict:
    data = _memory_read()
    data[key] = {"value": value, "writer": writer,
                 "revision": hashlib_sha1(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:12],
                 "updated_utc": datetime.now(timezone.utc).isoformat()}
    _memory_write(data)
    return {"ok": True, "key": key}


# ---------------------------------------------------------------------------
# Audit service (2.8 Information & News row: extends the system log)
# ---------------------------------------------------------------------------
def audit_query(**kw) -> Dict:
    return {"entries": read_audit_log(limit=kw.get("limit", 200)), "stats": get_audit_stats()}


def audit_integrity(**kw) -> Dict:
    return {"integrity": verify_log_integrity()}


# ---------------------------------------------------------------------------
# Money engine service (2.8 Money-Making Engine row)
# ---------------------------------------------------------------------------
def money_status(**_kw) -> Dict:
    from pathlib import Path
    rev = Path(__file__).resolve().parent.parent / ".jarvis" / "revenue.json"
    if not rev.exists():
        return {"total_earned": 0, "balance": 0, "verified": False}
    try:
        d = json.loads(rev.read_text(encoding="utf-8"))
        return {"total_earned": d.get("total_earned", 0),
                "balance": d.get("balance", 0),
                "transactions": len(d.get("transactions", [])),
                "verified": True}
    except Exception as e:
        return {"error": str(e), "verified": False}


def money_record(gateway: str, amount: float, currency: str, reference: str, **_kw) -> Dict:
    """Call the Payment Service (namibian_payments) — sensitive, requires capability."""
    from actions.namibian_payments import record_verified_income
    rec = record_verified_income(gateway, amount, currency, reference,
                                 proof=f"service_api:{reference}")
    return {"ok": bool(rec), "gateway": gateway, "amount": amount, "recorded": rec}


# ---------------------------------------------------------------------------
# Orchestrator service (2.8 Multi-agent orchestrator row)
# ---------------------------------------------------------------------------
def orchestrator_status(**_kw) -> Dict:
    return {"services": list_services(), "workers_registered": len(_SERVICES),
            "ts": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# The invoke gate — the PART 2.8 rule: equal-or-stricter permissions
# ---------------------------------------------------------------------------
def invoke_service(
    caller: str,
    service: str,
    method: str,
    params: Dict,
    autonomy_level: int = 4,
    granted: bool = False,
) -> Dict:
    """
    Invoke a Core service. If the service requires a sensitive capability, the
    request MUST go through the Permission Broker first. A caller can never
    receive a more permissive answer than a domain agent could.
    """
    svc = _SERVICES.get(service)
    if not svc:
        return {"success": False, "error": f"unknown_service:{service}"}
    handler = svc["handler"]
    if method == "help":
        return {"success": True, "service": service,
                "methods": [m for m in dir(handler) if not m.startswith("_")]}

    # Dispatch: handlers may be plain functions (valid methods: the function's
    # own name or call/invoke) or provider objects (method names an attribute).
    import inspect
    if inspect.isfunction(handler) or inspect.ismethod(handler):
        if method not in (handler.__name__, "call", "invoke"):
            return {"success": False, "error": f"unknown_method:{service}.{method}"}
        fn = handler
    else:
        fn = getattr(handler, method, None)
        if not callable(fn):
            return {"success": False, "error": f"unknown_method:{service}.{method}"}

    caps = svc["capabilities"]
    domain = f"os.{service}"

    # Non-sensitive services pass through directly
    if not any(c in SENSITIVE_CAPABILITIES for c in caps):
        try:
            return {"success": True, "service": service, "result": fn(**params)}
        except Exception as e:
            return {"success": False, "error": f"handler_error:{e}"}

    # Sensitive → permission broker gate (equal to agent path)
    needed = [c for c in caps if c in SENSITIVE_CAPABILITIES]
    import asyncio
    try:
        try:
            asyncio.get_running_loop()
            running = True
        except RuntimeError:
            running = False
        if running:
            return {"success": False, "error": "async_invoke_pending",
                    "mode": "awaiting_broker"}
        r = asyncio.run(_broker_request(caller, service, needed, domain,
                                        method, params, autonomy_level, granted))
    except Exception as e:
        return {"success": False, "error": f"broker_error:{e}"}
    if not r.get("success"):
        return {"success": False, **{k: v for k, v in r.items() if k != "success"}}
    try:
        return {"success": True, "service": service, "result": fn(**params)}
    except Exception as e:
        return {"success": False, "error": f"handler_error:{e}"}


async def _broker_request(caller, service, needed_caps, domain, method, params, autonomy_level, granted):
    return await request_permission(
        caller=caller, capability=needed_caps[0], domain=domain,
        action=method, params=params, reasoning=f"os service {service}.{method}",
        autonomy_level=autonomy_level, granted=granted,
    )


def core_status() -> Dict:
    """Shell status line (2.3.4): one-glance view of what Core is doing."""
    return {
        "services": list_services(),
        "permission_broker": broker_status(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Wiring: register all Core services (Part 2.8 Table 2.1)
# ---------------------------------------------------------------------------
def _register_all():
    register_service("memory", "0.1", [], memory_read)
    register_service("memory_write", "0.1", [], memory_write)
    register_service("audit", "0.1", ["network_egress"], audit_query)
    register_service("audit_integrity", "0.1", [], audit_integrity)
    register_service("money", "0.1", ["payments_txn"], money_status)
    register_service("money_record", "0.1", ["payments_txn"], money_record)
    register_service("orchestrator", "0.1", ["network_egress"], orchestrator_status)


_register_all()
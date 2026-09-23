"""
Permission Broker — JARVIS OS Figure 2.2 (Part 2.7.4, Table 2.1 Safety row).

A single, central entry point through which EVERY request for a sensitive
capability must pass. There is no side channel: no caller — domain agent,
shell, or future trustless app — reaches a sensitive capability except
through this broker.

Layers enforced, in order:
  1. Kill-switch / guardian state  (core.safety_guardian)
  2. Standing approval-gate list + autonomy ladder (core.approval_gate)
  3. Capability grants, revocable mid-session (no persistent bypass)
  4. Immutable audit trail for every grant and every denial (core.audit_log)

This is the OS-service version of the v1.0 approval gate: an app calling into
core cannot get a more permissive answer than a domain agent could.
"""
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from core.safety_guardian import get_safety_guardian, is_killed
from core.audit_log import write_audit_entry
from core.approval_gate import get_approval_gate, ApprovalStatus, request_approval

# ---------------------------------------------------------------------------
# Capability taxonomy (Figure 2.2 "sensitive capabilities")
# ---------------------------------------------------------------------------
SENSITIVE_CAPABILITIES = {
    "mic",
    "camera",
    "location",
    "contacts",
    "stored_credentials",
    "network_egress",
    "payments_txn",
    "door_locks",
    "telephony_sms",
    "file_write_outside",
    "screen_input",
    "audio_playback_out",
}

# Grant a caller a capability at boot only for cheap, non-sensitive things.
NON_SENSITIVE = {"clock", "math", "syntax_check", "search_public"}

# ---------------------------------------------------------------------------
# Grant store — revocable, per-caller, per-capability (Part 2.7.4)
# ---------------------------------------------------------------------------
_GRANT_LOCK = threading.Lock()


@dataclass
class Grant:
    caller: str
    capability: str
    granted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    granted_by: str = "boss"
    revoked: bool = False


_grants: Dict[str, Dict[str, Grant]] = {}  # caller -> capability -> Grant


def _identity(caller: str, capability: str) -> str:
    return f"{caller}|{capability}"


def grant_capability(caller: str, capability: str, granted_by: str = "boss") -> Dict:
    """Explicitly grant one capability to one caller (Layer 3 of the broker)."""
    if capability in SENSITIVE_CAPABILITIES:
        write_audit_entry(
            domain="permission_broker",
            action_proposed=f"grant:{capability}",
            screening_result="passed",
            gate_result=f"granted_by_{granted_by}",
            execution_result="success",
            real_outcome={"caller": caller, "capability": capability, "granted_by": granted_by},
            reasoning_summary=f"Explicit capability grant to {caller}",
            credential_used="none",
        )
    with _GRANT_LOCK:
        _grants.setdefault(caller, {})[capability] = Grant(
            caller=caller, capability=capability, granted_by=granted_by
        )
    return {"success": True, "caller": caller, "capability": capability}


def revoke_capability(caller: str, capability: str, revoked_by: str = "boss") -> Dict:
    """Revoke a capability mid-session. Takes effect immediately (Layer 3)."""
    with _GRANT_LOCK:
        gr = _grants.get(caller, {}).get(capability)
        if gr is None:
            return {"success": False, "error": "no grant to revoke"}
        gr.revoked = True
    write_audit_entry(
        domain="permission_broker",
        action_proposed=f"revoke:{capability}",
        screening_result="passed",
        gate_result=f"revoked_by_{revoked_by}",
        execution_result="success",
        real_outcome={"caller": caller, "capability": capability, "revoked_by": revoked_by},
        reasoning_summary=f"Capability {capability} revoked for {caller}",
        credential_used="none",
    )
    return {"success": True, "caller": caller, "capability": capability}


def has_capability(caller: str, capability: str) -> bool:
    """Check a standing grant WITHOUT going through the broker. RAISE if bypass."""
    with _GRANT_LOCK:
        gr = _grants.get(caller, {}).get(capability)
        return bool(gr and not gr.revoked)


# ---------------------------------------------------------------------------
# The broker itself
# ---------------------------------------------------------------------------
class PermissionBroker:
    """Single gate: request_sensitive → guardian → approval gate → grant check → audit."""

    def __init__(self):
        self._log: Dict[str, Dict] = {}
        self._log_lock = threading.Lock()

    # ---- Layer 1: guardian -------------------------------------------------
    def _guardian_check(self, caller: str, capability: str, domain: str) -> Optional[Dict]:
        if is_killed(domain):
            return {"success": False, "error": f"domain_killed:{domain}", "layer": "guardian"}
        if is_killed(caller):
            return {"success": False, "error": f"caller_killed:{caller}", "layer": "guardian"}
        return None

    # ---- Layer 4: audit ----------------------------------------------------
    def _audit(self, caller: str, capability: str, domain: str, result: str, detail: Any):
        try:
            write_audit_entry(
                domain=domain,
                action_proposed=f"capability:{capability}",
                screening_result="passed",
                gate_result=result,
                execution_result="success" if result.startswith("granted") else "denied",
                real_outcome={"caller": caller, "capability": capability, "detail": detail},
                reasoning_summary=f"permission_broker:{result} for {caller}",
                credential_used="none",
            )
        except Exception:
            pass

    # ---- Public entry point ------------------------------------------------
    async def request_sensitive(
        self,
        caller: str,
        capability: str,
        domain: str,
        action: str,
        params: Dict,
        reasoning: str,
        autonomy_level: int,
        granted: bool = False,
    ) -> Dict:
        """
        The ONLY way to reach a sensitive capability.

        - granted=True  → caller holds an explicit sliding grant (already spoke to
                          Boss or is standing-approved); checked and audited here.
        - granted=False → goes through the approval gate (autonomy ladder).
        """
        if capability not in SENSITIVE_CAPABILITIES:
            self._audit(caller, capability, domain, f"denied:not_sensitive:{capability}", {})
            return {"success": False, "error": "unknown_or_nonsensitive_capability", "layer": "broker"}

        # Layer 1 — guardian
        g = self._guardian_check(caller, capability, domain)
        if g is not None:
            self._audit(caller, capability, domain, "denied:guardian", g)
            return g

        # Layer 3 — explicit grant path
        if granted:
            with _GRANT_LOCK:
                standing = _grants.get(caller, {}).get(capability)
                ok = bool(standing and not standing.revoked)
            if ok:
                self._audit(caller, capability, domain, "granted:standing", {})
                return {"success": True, "layer": "broker", "mode": "standing_grant", "capability": capability}
            self._audit(caller, capability, domain, "denied:no_grant", {})
            return {"success": False, "error": "no_standing_grant", "layer": "broker"}

        # Layer 2 — approval gate / autonomy ladder (async)
        try:
            req = await request_approval(domain, action, params, reasoning, autonomy_level)
        except Exception as e:
            self._audit(caller, capability, domain, f"denied:gate_error:{e}", {})
            return {"success": False, "error": f"gate_error:{e}", "layer": "broker"}

        if not req.get("success"):
            self._audit(caller, capability, domain, f"denied:{req.get('error')}", req)
            return {"success": False, "error": req.get("error"), "layer": "approval_gate"}

        if req.get("status") == ApprovalStatus.AUTO_APPROVED.value:
            self._audit(caller, capability, domain, "granted:auto_approved", req)
            return {"success": True, "layer": "broker", "mode": "auto_approved", "capability": capability,
                    "request_id": req.get("request_id")}

        # Pending — Boss must decide
        self._audit(caller, capability, domain, "pending:awaiting_boss", req)
        return {"success": False, "layer": "broker", "mode": "awaiting_boss",
                "request_id": req.get("request_id"),
                "message": "Awaiting Boss approval", "requires_approval": True}

    # ---- Visibility (Part 2.3.4: shell shows live status from audit) --------
    def recent_decisions(self, limit: int = 20) -> List[Dict]:
        with self._log_lock:
            items = [dict(v) for v in self._log.values()]
        items.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return items[:limit]


# ---------------------------------------------------------------------------
# Singleton + convenience
# ---------------------------------------------------------------------------
_broker: Optional[PermissionBroker] = None


def get_permission_broker() -> PermissionBroker:
    global _broker
    if _broker is None:
        _broker = PermissionBroker()
    return _broker


async def request_permission(
    caller: str,
    capability: str,
    domain: str,
    action: str,
    params: Dict,
    reasoning: str,
    autonomy_level: int,
    granted: bool = False,
) -> Dict:
    """Convenience async wrapper — the single entry point all callers should use."""
    return await get_permission_broker().request_sensitive(
        caller, capability, domain, action, params, reasoning, autonomy_level, granted
    )


def broker_status() -> Dict:
    """Non-sensitive introspection used by the shell status line (2.3.4)."""
    with _GRANT_LOCK:
        grants = {
            caller: {cap: (not g.revoked) for cap, g in cg.items()}
            for caller, cg in _grants.items()
        }
    return {
        "service": "permission_broker",
        "sensitive_capabilities": sorted(SENSITIVE_CAPABILITIES),
        "standing_grants": grants,
        "layers": ["guardian", "approval_gate", "grants", "audit"],
    }
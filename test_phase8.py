"""Phase 8 — JARVIS OS: Permission Broker (Figure 2.2) verification."""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

from core.permission_broker import (
    get_permission_broker, grant_capability, revoke_capability,
    request_permission, broker_status, SENSITIVE_CAPABILITIES,
)
from core.safety_guardian import (
    get_safety_guardian, trigger_kill, is_killed, KillLayer, KillReason,
)
from core.audit_log import read_audit_log

passed = 0
failed = []

def check(name, cond, extra=""):
    global passed
    if cond:
        passed += 1
        print(f"  OK  {name}")
    else:
        failed.append(name)
        print(f"  FAIL {name} {extra}")

print("=== PHASE 8 VERIFICATION: PERMISSION BROKER (OS Fig 2.2) ===")

async def main():
    broker = get_permission_broker()

    # 1. All sensitive capabilities enumerated
    check("capability taxonomy present", SENSITIVE_CAPABILITIES >= {
        "mic", "camera", "location", "contacts", "stored_credentials",
        "network_egress", "payments_txn", "door_locks", "telephony_sms"})

    # 2. Non-sensitive call rejected without going to a grant (no side channel)
    r = await request_permission("agentA", "clock", "test_domain", "read", {},
                                 "want time", 4)
    check("non-sensitive capability rejected by broker", not r.get("success")
          and r.get("error") == "unknown_or_nonsensitive_capability")

    # 3. Guardian kill blocks BEFORE any approval (Layer 1)
    stop_layer = KillLayer.LOCAL_STOP
    trigger_kill(stop_layer, KillReason.MANUAL_LOCAL, "killed_domain", {"drill": True})
    r = await request_permission("agentB", "mic", "killed_domain", "record", {},
                                 "record", 4)
    check("killed domain blocked by broker (layer 1)", not r.get("success")
          and "killed" in r.get("error", ""))
    g = get_safety_guardian()
    g.acknowledge_domain_kills("killed_domain", boss_confirmed=True)

    # 4. Auto-approved path (autonomy >= 3) logs granted + returns success
    r = await request_permission("agentC", "search", "research", "web", {},
                                 "search", 4) if False else \
        await request_permission("agentC", "network_egress", "net_domain", "fetch", {},
                                 "fetch page", 4)
    check("sensitive w/ high autonomy auto-approved",
          r.get("success") and r.get("mode") == "auto_approved")

    # 5. Low autonomy => awaiting Boss (Level <= 2)
    r2 = await request_permission("agentD", "mic", "voice_domain", "record", {},
                                  "record audio", 1)
    check("low autonomy pending approval", not r2.get("success")
          and r2.get("mode") == "awaiting_boss" and r2.get("requires_approval"))

    # 6. No standing grant => denied (Layer 3)
    r3 = await request_permission("agentE", "camera", "cam_domain", "snap", {},
                                  "take photo", 4, granted=True)
    check("no standing grant denied", not r3.get("success")
          and r3.get("error") == "no_standing_grant")

    # 7. Standing grant issued => passed through broker
    grant_capability("agentF", "camera", granted_by="boss")
    r4 = await request_permission("agentF", "camera", "cam_domain", "snap", {},
                                  "take photo", 4, granted=True)
    check("standing grant honored", r4.get("success") and r4.get("mode") == "standing_grant")

    # 8. Mid-session revoke drill (Part 4.3) takes effect immediately
    grant_capability("agentF", "mic", granted_by="boss")
    before = await request_permission("agentF", "mic", "voice_domain", "record", {},
                                      "record", 4, granted=True)
    check("grant active before revoke", before.get("success"))
    revoke_capability("agentF", "mic", revoked_by="boss")
    after = await request_permission("agentF", "mic", "voice_domain", "record", {},
                                     "record", 4, granted=True)
    check("revoke takes effect immediately (drill 4.3)", not after.get("success")
          and after.get("error") == "no_standing_grant")

    # 9. Audit trail: every grant/deny/revoke is in the immutable log
    entries = read_audit_log(domain=None, limit=100) or []
    bl = [e for e in entries if e.get("domain", "") in ("permission_broker", "voice_domain",
                                                        "net_domain", "cam_domain", "research")]
    check("broker actions in audit log", len(bl) >= 6, f"({len(bl)} found)")

    # 10. broker_status exposes grants + layers (shell status line 2.3.4)
    st = broker_status()
    check("broker_status layers", st["layers"] == ["guardian", "approval_gate", "grants", "audit"])
    check("broker_status shows revoke took effect",
          st["standing_grants"].get("agentF", {}).get("mic") is False)

    # 11. Guardian state remains clean afterwards (no leakage into other phases)
    check("guardian not mutated by broker tests", not is_killed("research"))

    print(f"\n=== PHASE 8: {passed} passed, {len(failed)} failed ===")
    if failed:
        print("  FAILED:", failed)
        return 1
    print("=== PHASE 8 COMPLETE ===")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
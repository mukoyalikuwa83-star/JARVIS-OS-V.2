"""Phase 9 — JARVIS OS: Core Services stable API (Part 2.8) verification."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

from core.service_api import (
    list_services, invoke_service, memory_read, memory_write,
    audit_query, audit_integrity, money_status, orchestrator_status, core_status,
)

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

print("=== PHASE 9 VERIFICATION: CORE SERVICES API (OS Part 2.8) ===")

# 1. Service registry populated per Table 2.1
svcs = list_services()
expected = {"memory", "memory_write", "audit", "audit_integrity",
            "money", "money_record", "orchestrator"}
check("all core services registered", expected.issubset(set(svcs.keys())), str(svcs.keys()))

# 2. Non-sensitive service works directly — memory_write (handler __name__ = "memory_write")
wr = invoke_service("shell", "memory_write", "memory_write",
                    {"key": "os_test", "value": "hello", "writer": "shell"}, 4)
check("memory_write via service", wr.get("success") and wr.get("result", {}).get("ok"))

# 3. memory_read (handler __name__ = "memory_read")
rd = invoke_service("shell", "memory", "memory_read", {"key": "os_test"}, 4)
check("memory_read via service", rd.get("success")
      and rd.get("result", {}).get("found") and rd["result"]["value"]["value"] == "hello")

# 4. Audit service returns real data (handler __name__ = "audit_query")
aq = invoke_service("shell", "audit", "audit_query", {"limit": 50}, 4)
check("audit query via service", aq.get("success") and "entries" in aq.get("result", {}))

# 5. Audit integrity via service
ai = invoke_service("shell", "audit_integrity", "audit_integrity", {}, 4)
check("audit integrity service", ai.get("success")
      and ai.get("result", {}).get("integrity", {}).get("valid") is True)

# 6. Money service reflects real revenue state (handler __name__ = "money_status")
ms = invoke_service("shell", "money", "money_status", {}, 4)
check("money status service", ms.get("success")
      and ms["result"].get("verified") and ms["result"].get("balance") == 535.0,
      str(ms))

# 7. Permission-broker gate: sensitive money_record WITHOUT standing grant
#    and with autonomy_level=1 (below auto-approve threshold) does NOT run handler
#    — proves Part 2.8 no-bypass rule and avoids polluting revenue.json
mr = invoke_service("shell", "money_record", "money_record",
                    {"gateway": "bank_transfer", "amount": 99, "currency": "NAD",
                     "reference": "OS-TEST-NOGRANT"}, 1, granted=False)
check("money_record gated (no bypass, handler not invoked)",
      (not mr.get("success")) and mr.get("mode") in ("awaiting_boss", "awaiting_broker"),
      str(mr)[:120])

# 8. Unknown service/method refuse cleanly
check("unknown service refused",
      not invoke_service("shell", "nope", "x", {}, 4).get("success"))
check("unknown method refused",
      not invoke_service("shell", "memory", "not_a_method", {}, 4).get("success"))

# 9. core_status assembles the one-glance shell line (2.3.4)
cs = core_status()
check("core_status has services + broker",
      "services" in cs and "permission_broker" in cs)

# 10. Sensitive-path audit: broker gating is logged (immutability preserved)
from core.audit_log import read_audit_log
ents = [e for e in read_audit_log(limit=200)
        if e.get("domain", "").startswith("os.money")
        or e.get("domain", "") == "permission_broker"]
check("sensitive service gating audited", len(ents) >= 1, f"({len(ents)} found)")

# 11. revenue.json not polluted by the gated test
rev = json.loads(Path(r"C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main\.jarvis\revenue.json").read_text(encoding="utf-8"))
check("revenue.json not polluted by invoke_service test",
      all("OS-TEST-NOGRANT" not in str(t.get("reference","")) for t in rev.get("transactions",[])))

print(f"\n=== PHASE 9: {passed} passed, {len(failed)} failed ===")
if failed:
    print("  FAILED:", failed)
    sys.exit(1)
print("=== PHASE 9 COMPLETE ===")
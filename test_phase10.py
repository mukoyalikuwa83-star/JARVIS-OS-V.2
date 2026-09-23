"""Phase 10 — JARVIS OS: SyncStore cross-device client contract (Part 2.9)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

from core.syncstore import (
    store_read, store_write, store_delete, store_list, list_conflicts,
    resolve_conflict, remote_status, remote_configure, handoff, continue_handoff,
)
from core.service_api import invoke_service, list_services

KEY = "os_sync_dp"
TEST_START = datetime.now(timezone.utc).isoformat()
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

# Clean slate for this test key
store_delete(KEY)
for ck in [k for k in (store_list().get("keys") or {}) if k.startswith(f"_conflicts.{KEY}.")]:
    store_delete(ck)

print("=== PHASE 10 VERIFICATION: SYNCSTORE (OS Part 2.9) ===")

# 1. Write + read roundtrip, revision present
w1 = store_write(KEY, {"step": 1}, writer="device_a")
check("write ok with revision", w1.get("ok") and w1.get("rev") and len(w1["rev"]) == 12, str(w1))
r1 = store_read(KEY)
check("read finds doc with matching rev", r1.get("found") and r1["rev"] == w1["rev"], str(r1))

# 2. Sequential write with correct expected_rev succeeds (lineage continues)
w2 = store_write(KEY, {"step": 2}, writer="device_a", expected_rev=w1["rev"])
check("sequential write with correct rev", w2.get("ok") and not w2.get("conflict"))

# 3. Shared memory: SyncStore sees the same store as core.service_api  (2.9.1)
svc = invoke_service("shell", "syncstore", "status", {}, 4)
check("syncstore registered as Core service", "syncstore" in list_services(),
      str(list_services().keys()))
check("syncstore served through invoke_service (object dispatch)",
      svc.get("success") and KEY in (svc.get("result", {}).get("keys") or {}),
      str(svc)[:120])

# 4. 2.9.2 cross-device handoff: rev carried, continuation succeeds
h = handoff("os_sync_handoff", {"from": "device_a"})
check("handoff creates rev", h.get("ok") and h.get("rev"))
cont = continue_handoff("os_sync_handoff", {"continued": True}, expected_rev=h["rev"])
check("handoff continuation on device B", cont.get("ok") and not cont.get("conflict"), str(cont))
store_delete("os_sync_handoff")

# 5. THAT is never silently dropped — stale write produces a documented conflict
stale = store_write(KEY, {"step": 999}, writer="stale_device", expected_rev=w1["rev"])
check("stale write rejected as conflict", not stale.get("ok") and stale.get("conflict"), str(stale))
check("conflict recorded", stale.get("recorded") is True)
check("stale value preserved under quarantine",
      stale.get("quarantined_under")
      and store_read(stale["quarantined_under"]).get("found"),
      str(stale))
check("live doc NOT corrupted by stale write",
      store_read(KEY)["rev"] == w2["rev"] and store_read(KEY)["value"] == {"step": 2})

# 6. Conflict appears in the append-only ledger
cf = list_conflicts()
unresolved = [c for c in cf if c.get("key") == KEY and c.get("status") == "unresolved"
              and c.get("ts", "") >= TEST_START]
check("conflict flagged in ledger with both sides",
      len(unresolved) == 1 and "incoming_value" in unresolved[0]
      and "current_value" in unresolved[0], str(unresolved)[:160])

# 7. Explicit resolution — keep quarantined ('their') side, nothing lost
res = resolve_conflict(KEY, keep="their", writer="operator")
check("resolution succeeds", res.get("ok") and res.get("kept") == "their", str(res))
check("resolved value is the quarantined incoming value",
      store_read(KEY)["value"] == {"step": 999})
check("quarantine key cleaned after resolution",
      not any(k.startswith(f"_conflicts.{KEY}.") for k in store_list()["keys"]))
unresolved_after = [c for c in list_conflicts()
                    if c.get("key") == KEY and c.get("status") == "unresolved"
                    and c.get("ts", "") >= TEST_START]
check("ledger marks conflict resolved", len(unresolved_after) == 0,
      str(unresolved_after)[:120])

# 8. Stale DELETE also guarded (conflict, current doc retained)
d_stale = store_delete(KEY, expected_rev="badstale000000")
check("stale delete rejected", not d_stale.get("ok") and d_stale.get("conflict"))
check("doc retained after stale delete", store_read(KEY).get("found"))
d = store_delete(KEY, expected_rev=store_read(KEY)["rev"])
check("good delete works", d.get("ok") and d.get("deleted"))
check("doc gone", not store_read(KEY).get("found"))

# 9. Remote contract (M3 hook) — local-only today, truthful about it
rs = remote_status()
check("remote_status reports local-only mode", rs.get("mode") == "local"
      and rs.get("local_only") is True, str(rs))
cfg = remote_configure("https://couch.example.com/sync")
check("remote_configure switches mode", cfg.get("mode") == "remote")
check("status reflects configured endpoint",
      remote_status().get("endpoint") == "https://couch.example.com/sync")
remote_configure(None)

# 10. No cross-contamination of other memory keys
check("pre-existing memory keys untouched",
      any(k == "os_test" for k in store_list()["keys"]))

print(f"\n=== PHASE 10: {passed} passed, {len(failed)} failed ===")
if failed:
    print("  FAILED:", failed)
    sys.exit(1)
print("=== PHASE 10 COMPLETE ===")
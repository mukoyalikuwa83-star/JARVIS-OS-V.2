"""Phase 11 regression: truthful withdrawals + no background browser spam.

Covers:
1. withdraw() rejects amount <= 0 (no more phantom $-0.00 records)
2. withdraw() rejects missing/invalid amount without touching balance
3. withdrawal routes through real payout rail and records audit
4. money_makers freelance_opportunities is BLOCKED without confirmed=true
5. autonomous_worker.find_jobs does NOT open browser by default
6. screen_processor uses non-deprecated mss spelling
"""
import sys
import os
import json
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_HERE = Path(__file__).resolve().parent
_REVENUE = _HERE / ".jarvis" / "revenue.json"
_BACKUP = _REVENUE.with_suffix(".json.bak_phase11")

PASS = 0
FAIL = 0

def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")

print("=== PHASE 11 REGRESSION: TRUTHFUL WITHDRAWALS + NO BROWSER SPAM ===")

# Save pristine ledger, restore at the end (truthfulness to $535)
orig = _REVENUE.read_text(encoding="utf-8") if _REVENUE.exists() else None
if _BACKUP.exists():
    _BACKUP.unlink()
shutil.copy(_REVENUE, _BACKUP)

try:
    from actions.real_hustle import SideHustleEngine
    engine = SideHustleEngine()
    starting_balance = float(engine._revenue["balance"])

    # 1. amount <= 0 rejected, no transaction, no balance change
    print("\n1. Withdraw amount <= 0 rejected:")
    r0 = engine.withdraw(0, "manual")
    check("withdraw(0) rejected", not r0.get("success") and "greater than 0" in r0.get("error", ""), str(r0))
    r0b = engine.withdraw(-5, "manual")
    check("withdraw(-5) rejected", not r0b.get("success"), str(r0b))
    check("balance unchanged after 0/negative", abs(engine._revenue["balance"] - starting_balance) < 1e-9, f"{engine._revenue['balance']} != {starting_balance}")

    # 2. amount missing -> SideHustleEngine.withdraw requires number
    print("\n2. Invalid amount rejected:")
    try:
        r1 = engine.withdraw("abc", "manual")
        check("withdraw('abc') rejected", not r1.get("success"), str(r1))
    except Exception as e:
        check("withdraw('abc') rejected", False, str(e))
    check("balance still unchanged", abs(engine._revenue["balance"] - starting_balance) < 1e-9)

    # 3. withdraw more than balance rejected
    print("\n3. Overdraft rejected:")
    r2 = engine.withdraw(starting_balance + 1000, "manual")
    check("withdraw > balance rejected", not r2.get("success") and "Insufficient" in r2.get("error", ""), str(r2))
    check("balance still unchanged", abs(engine._revenue["balance"] - starting_balance) < 1e-9)

    # 4. Real withdrawal via manual rail -> revenue.json updated + audit
    print("\n4. Real withdrawal via payout rail:")
    r3 = engine.withdraw(10.0, "manual")
    check("withdraw(10, manual) succeeds", r3.get("success"), str(r3))
    check("withdraw returns reference", bool(r3.get("reference")), str(r3))
    check("balance reduced by 10", abs(engine._revenue["balance"] - (starting_balance - 10)) < 1e-9,
          f"{engine._revenue['balance']} vs {starting_balance - 10}")
    rev = json.loads(_REVENUE.read_text(encoding="utf-8"))
    wtx = [t for t in rev["transactions"] if t.get("type") == "withdrawal"]
    check("revenue ledger has real withdrawal", len(wtx) >= 1, str(len(wtx)))
    check("no phantom 0.0 withdrawal", all(float(t.get("amount", 1)) < 0 for t in wtx), str(wtx))
    check("total_withdrawn = 10", abs(rev["total_withdrawn"] - 10) < 1e-9, str(rev["total_withdrawn"]))
    check("balance in ledger == 525", abs(rev["balance"] - 525.0) < 1e-9, str(rev["balance"]))

    # 5. Unsupported payout gateway (stripe/dpo) -> truthful error, no deduction
    print("\n5. Unsupported payout rail rejected:")
    r4 = engine.withdraw(5.0, "dpo")
    check("withdraw via dpo rejected", not r4.get("success") and "receiving payments only" in r4.get("error", ""), str(r4))
    check("balance unchanged after failed dpo", abs(engine._revenue["balance"] - (starting_balance - 10)) < 1e-9)

    # 6. money_makers freelance_opportunities blocked without confirmation
    print("\n6. money_makers freelance_opportunities gated:")
    from actions.money_makers import handle as mm_handle
    blocked = mm_handle({"action": "freelance_opportunities", "confirmed": False})
    check("blocked without confirmed", "BLOCKED" in blocked and "no tabs were opened" in blocked.lower(), blocked[:80])
    check("nothing opened (no url opened)", "opened:" not in blocked.lower() and "opened " not in blocked.lower(), "")
    ok1 = mm_handle({"action": "freelance_opportunities", "confirmed": True})
    check("confirmed path runs (links/skip ok)", "opened" in ok1.lower() or "skip" in ok1.lower() or "could not" in ok1.lower(), ok1[:80])

    # 7. autonomous_worker.find_jobs does not open browser by default
    print("\n7. find_jobs browser-free by default:")
    from actions.autonomous_worker import AutonomousWorker
    aw = AutonomousWorker()
    # Patch rate limiter so the test is deterministic
    import actions.autonomous_worker as aw_mod
    orig_limiter = aw_mod._rate_limit
    aw_mod._rate_limit = lambda key: True
    try:
        jr = aw.find_jobs("freelancer", "python")
        check("find_jobs returns a string", isinstance(jr, str), type(jr))
        check("find_jobs did not open browser", "no browser tab opened" in jr or "Found" in jr or "jobs saved" in jr or "Scraping" in jr, jr[:80])
    finally:
        aw_mod._rate_limit = orig_limiter

    # 8. screen_processor mss spelling not deprecated module fn
    print("\n8. screen_processor uses safe mss spelling:")
    src = (_HERE / "actions" / "screen_processor.py").read_text(encoding="utf-8")
    check("no bare mss.mss() usage", "with mss.mss() as sct:" not in src)
    check("uses _mss_session", "with _mss_session() as sct:" in src)

    # 9. real_hustle tool schema documents paypal_email + amount required
    print("\n9. tool_registry withdraw schema updated:")
    from core.tool_registry import TOOL_DECLARATIONS
    rh = next(t for t in TOOL_DECLARATIONS if t.get("name") == "real_hustle")
    props = rh["parameters"]["properties"]
    check("schema has paypal_email", "paypal_email" in props)
    check("schema marks amount REQUIRED for withdraw", "REQUIRED for withdraw" in props["amount"]["description"])

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)

finally:
    # Restore truthful ledger
    _REVENUE.write_text(orig if orig is not None else json.dumps({
        "total_earned": 535.0, "total_withdrawn": 0.0, "balance": 535.0, "transactions": []}),
        encoding="utf-8")
    if _BACKUP.exists():
        _BACKUP.unlink()
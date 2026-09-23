"""Phase 7 prep: verified income loop test — gateway confirmations must record revenue + audit, idempotent, reconcilable."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from actions.namibian_payments import verify_payment, record_verified_income, handle as pay_handle
from actions.reconciliation import reconcile_30d, format_report
from core.audit_log import write_audit_entry, search_audit
import json

print("=== PHASE 7 PREP: VERIFIED INCOME LOOP ===")

# 1. PayPal webhook COMPLETED (trusted webhook, no live API creds needed)
print("\n1. Verify PayPal webhook (COMPLETED order):")
v = verify_payment("paypal", "QPD123", webhook_data={
    "id": "QPD123",
    "status": "COMPLETED",
    "purchase_units": [{"amount": {"value": "25.00", "currency_code": "USD"}}],
})
print(f"   verify returned: {v}")
assert v.get("verified") and v.get("recorded"), f"PayPal verification should record income: {v}"
print("   -> PayPal verified + income recorded: OK")

# 2. Idempotence: re-verifying same order must NOT double-record
print("\n2. Re-verify same PayPal order (idempotence):")
v2 = verify_payment("paypal", "QPD123", webhook_data={
    "id": "QPD123", "status": "COMPLETED",
    "purchase_units": [{"amount": {"value": "25.00", "currency_code": "USD"}}],
})
print(f"   second verify recorded={v2.get('recorded')}")
assert v2.get("recorded") is False, "Re-verification must not double-record"
print("   -> no double-count: OK")

# 3. DPO webhook success (Result '00')
print("\n3. Verify DPO webhook (success result '00'):")
v3 = verify_payment("dpo", "REF-DPO-1", webhook_data={
    "TransactionToken": "TK-777",
    "Result": "00",
    "TransactionReference": "REF-DPO-1",
    "Amount": "250",
    "Currency": "NAD",
})
print(f"   verify returned: {v3}")
assert v3.get("verified") and v3.get("recorded")
print("   -> DPO verified + income recorded: OK")

# 4. Manual bank transfer confirmation (Boss confirms receipt)
print("\n4. Manual bank transfer confirmation:")
r = pay_handle({"action": "record_verified_income", "target": "bank_transfer,150,NAD,BT-REF-9"})
print(f"   {r}")
assert "recorded" in r.lower()
r2 = pay_handle({"action": "record_verified_income", "target": "bank_transfer,150,NAD,BT-REF-9"})
print(f"   repeat: {r2}")
assert "already recorded" in r2.lower()
print("   -> bank transfer recorded + idempotent: OK")

# 5. Audit trail exists for all three
print("\n5. Audit trail check:")
hits = search_audit("payment_received", limit=20)
print(f"   audit entries with payment_received: {len(hits)}")
assert len(hits) >= 3
for h in hits[:5]:
    print(f"     {h['domain']}: {h['action_proposed']} {h['real_outcome']}")
print("   -> audit trail present: OK")

# 6. Reconciliation now matches verified income (no unlogged for these sources)
print("\n6. Reconciliation after verified income:")
rep = reconcile_30d(days=30, include_test=False)
print(f"   verdict: {rep['verdict']}")
print(f"   reported_income: {rep['revenue']['reported_income']}")
print(f"   unlogged_income: {[u['source'] for u in rep['exceptions']['unlogged_income']]}")
# The verified sources (paypal, dpo, bank_transfer) must NOT appear as unlogged
unlogged_sources = [u["source"] for u in rep["exceptions"]["unlogged_income"]]
assert "paypal" not in unlogged_sources, "paypal income must be reconcilable"
assert "dpo" not in unlogged_sources, "dpo income must be reconcilable"
assert "bank_transfer" not in unlogged_sources, "bank_transfer income must be reconcilable"
print("   -> verified income recognised: OK")

print("\n=== PHASE 7 PREP: ALL GREEN ===")

# 7. Self-cleanup: remove test-only verified income so the ledger stays truthful
#    (the flagged webhook refs were fabricated by this test, not real payments).
_TEST_REFS = {"QPD123", "REF-DPO-1", "BT-REF-9"}
_rev_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jarvis", "revenue.json")
if os.path.exists(_rev_path):
    with open(_rev_path, "r", encoding="utf-8") as _f:
        _rev = json.load(_f)
    _removed = 0
    _keep = []
    for _t in _rev.get("transactions", []):
        if _t.get("ref") in _TEST_REFS:
            _removed += 1
        else:
            _keep.append(_t)
    if _removed:
        _rev["transactions"] = _keep
        _test_income = sum(float(t.get("amount", 0)) for t in _keep if t.get("type") == "income")
        _rev["total_earned"] = _test_income
        _rev["balance"] = _test_income - float(_rev.get("total_withdrawn", 0))
        with open(_rev_path, "w", encoding="utf-8") as _f:
            json.dump(_rev, _f, indent=2)
        print(f"7. Cleanup: removed {_removed} test-only webhook income rows "
              f"(ledger balance restored to ${_rev['balance']:.2f})")
print("\n=== PHASE 7: ALL GREEN (ledger restored to truthful state) ===")
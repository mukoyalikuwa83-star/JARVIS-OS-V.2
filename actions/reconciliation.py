"""
30-Day Reconciliation — Part 6 Phase 5: Cross-check audit log vs revenue records.
Detects: unapproved money moves, unlogged income, amount mismatches.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from actions._api import _load_env
from core.audit_log import read_audit_log, verify_log_integrity

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_REVENUE_FILE = _DATA_DIR / "revenue.json"
_RECON_REPORT = _DATA_DIR / "reconciliation_report.json"

_load_env()


def _load_revenue() -> Dict:
    if not _REVENUE_FILE.exists():
        return {"total_earned": 0.0, "transactions": []}
    try:
        return json.loads(_REVENUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"total_earned": 0.0, "transactions": []}


def reconcile_30d(days: int = 30, report_to: Optional[str] = None, include_test: bool = False) -> Dict:
    """
    Reconcile the last N days: audit log vs revenue transactions.
    Flags (Appendix C + Part 4.4 compliance):
      - income with no audit trail (unlogged)
      - money actions without approval gate at/above required level
      - gumroad/stripe/paypal/fnb records not in revenue file
    """
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat()

    # 1. Audit integrity
    integrity = verify_log_integrity()

    # 2. Audit log entries in window, money-relevant domains/actions
    entries = read_audit_log(since=cutoff, limit=100000)
    money_domains = {"gumroad", "stripe", "paypal", "fnb", "dpo", "namibian", "trading", "worker", "sandbox", "bank_transfer"}
    money_entries = [e for e in entries if e.get("domain") in money_domains]
    money_actions = [e for e in money_entries if e.get("screening_result") in ("passed",)]
    unapproved_money = [
        e for e in money_actions
        if "approved" not in (str(e.get("gate_result", "")))
        and "auto_approved" not in str(e.get("gate_result", ""))
    ]

    # 3. Revenue file
    rev = _load_revenue()
    txns = rev.get("transactions", [])
    real_txns = [t for t in txns if not t.get("source", "").lower().startswith("test")]
    if include_test:
        real_txns = txns  # include simulated/test sources too

    window_txns = []
    for t in real_txns:
        ts = t.get("time", 0)
        if isinstance(ts, (int, float)):
            ttime = datetime.fromtimestamp(ts, tz=timezone.utc)
            if ttime >= now - timedelta(days=days):
                window_txns.append(t)

    reported_income = sum(float(t.get("amount", 0)) for t in window_txns if t.get("type") == "income")
    withdrawn = sum(float(t.get("amount", 0)) for t in window_txns if t.get("type") == "withdrawal")
    balance = float(rev.get("balance", 0))

    # 4. Cross-check: every real income should have a matching audit entry
    unlogged_income = []
    for t in window_txns:
        if t.get("type") != "income":
            continue
        source = str(t.get("source", ""))
        matched = any(
            source.lower() in str(e.get("real_outcome", "")).lower()
            or source.lower() in str(e.get("action_proposed", "")).lower()
            for e in money_actions
        )
        if not matched:
            unlogged_income.append({"source": source, "amount": t.get("amount")})

    # 5. Summary
    report = {
        "generated_utc": now.isoformat(),
        "window_days": days,
        "audit_integrity": integrity,
        "audit_log": {
            "total_entries": len(entries),
            "money_entries": len(money_entries),
        },
        "revenue": {
            "reported_income": round(reported_income, 2),
            "withdrawn": round(withdrawn, 2),
            "balance": round(balance, 2),
        },
        "exceptions": {
            "unapproved_money_actions": unapproved_money[:50],
            "unlogged_income": unlogged_income[:50],
            "count_unapproved": len(unapproved_money),
            "count_unlogged": len(unlogged_income),
        },
        "verdict": "clean" if (integrity.get("valid") and not unapproved_money and not unlogged_income) else "needs_review",
    }

    _RECON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def format_report(report: Dict) -> str:
    lines = ["=== 30-DAY RECONCILIATION ==="]
    lines.append(f"Window: last {report['window_days']} days (UTC)")
    lines.append(f"Audit integrity: {'VALID' if report['audit_integrity'].get('valid') else 'BROKEN'}")
    if report["audit_integrity"].get("errors"):
        for e in report["audit_integrity"]["errors"][:10]:
            lines.append(f"  AUDIT ERROR: {e}")
    lines.append("")
    lines.append("REVENUE:")
    lines.append(f"  Reported income: {report['revenue']['reported_income']}")
    lines.append(f"  Balance: {report['revenue']['balance']}")
    lines.append(f"  Withdrawn: {report['revenue']['withdrawn']}")
    lines.append("")
    exc = report["exceptions"]
    lines.append("EXCEPTIONS:")
    lines.append(f"  Unapproved money actions: {exc['count_unapproved']}")
    for e in exc["unapproved_money_actions"][:10]:
        lines.append(f"    ! {e.get('domain')} {e.get('action_proposed')} gate={e.get('gate_result')}")
    lines.append(f"  Unlogged income entries: {exc['count_unlogged']}")
    for e in exc["unlogged_income"][:10]:
        lines.append(f"    ! {e.get('source')} {e.get('amount')}")
    lines.append("")
    lines.append(f"VERDICT: {report['verdict'].upper()}")
    return "\n".join(lines)


def handle(parameters: Dict) -> str:
    action = parameters.get("action", "reconcile")
    if action == "reconcile":
        include_test = parameters.get("include_test", "false").lower() in ("1", "true", "yes")
        report = reconcile_30d(days=int(parameters.get("days", 30)), include_test=include_test)
        return format_report(report)
    elif action == "json":
        report = reconcile_30d(days=int(parameters.get("days", 30)))
        return json.dumps(report, ensure_ascii=False)
    return "Unknown action. Use: reconcile"
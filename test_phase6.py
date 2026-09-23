"""Phase 6 verification: end-to-end dry run — scan -> score -> screen -> sandbox -> approve -> publish -> report."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_phase6():
    print("=== PHASE 6 END-TO-END DRY RUN ===")

    # 1. Opportunity Discovery: scan -> score -> screen (Appendix D)
    print("\n1. Opportunity Discovery:")
    from actions.opportunity_discovery import OpportunityDiscoveryAgent
    opp = OpportunityDiscoveryAgent()
    scan = await opp.handle("scan_opportunities", {"limit": 3})
    print(f"   Scan result ok: {scan.get('success')}")

    # Screen a high-risk idea against Appendix D exclusion list
    risky = await opp.handle("screen_idea", {"idea": {"title": "Crypto pump signals", "description": "guaranteed returns with fake accounts, pump and dump manipulation"}})
    print(f"   Screen high-risk idea rejected: {not risky.get('approved', risky.get('passed'))} ({risky.get('screening_result', risky.get('reason', ''))[:60]})")

    # 2. Publish via content engine (gates approval)
    print("\n2. Content Engine (approval gating):")
    from actions.content_engine import ContentEngineAgent
    ce = ContentEngineAgent()
    draft = await ce.handle("create_content", {"content_type": "blog_post", "channel": "blog", "topic": "Python automation"})
    print(f"   Draft ok: {draft.get('success')}")
    draft_id = draft.get("draft", {}).get("id") or list(ce._drafts.keys())[0]
    review = await ce.handle("review_content", {"draft_id": draft_id, "action": "approve"})
    print(f"   Review approve ok: {review.get('success')}")
    pub = await ce.handle("publish_content", {"draft_id": draft_id, "channel": "blog"})
    print(f"   Publish blocked (track record < 10): {not pub.get('success')}, requires_approval: {pub.get('requires_approval')}")

    # 3. Sandbox trading: place + close with real PnL
    print("\n3. Sandbox Trading:")
    from actions.sandbox_trading import get_sandbox_engine, SandboxConfig, SandboxMode
    sandbox = get_sandbox_engine()
    sid = await sandbox.create_session(SandboxConfig(mode=SandboxMode.PAPER, starting_capital=10000))
    o = await sandbox.place_order(sid, "BTC", "long", 0.005)
    print(f"   Place order: {o.get('success')}")
    c = await sandbox.close_position(sid, "BTC")
    print(f"   Close position: {c.get('success')}, pnl: {round(c.get('pnl', 0), 2)}")

    # 4. Approval gate for a money action
    print("\n4. Approval Gate:")
    from core.approval_gate import get_approval_gate
    gate = get_approval_gate()
    req = await gate.submit_request("money", "withdrawal", {"amount": 500}, "Withdrawal request", 1)
    print(f"   Withdrawal request: {req['status']}, requires_approval: {req['requires_approval']}")

    # 5. Computer control: bounded autonomy check
    print("\n5. Computer Control Gating:")
    from actions.computer_control import ComputerControlAgent
    cc = ComputerControlAgent()
    can, needs, reason = cc.can_execute("delete_file")  # always-requires-approval
    print(f"   delete_file requires approval: {needs}")
    can, needs, reason = cc.can_execute("launch_app")
    print(f"   Level {cc.config.autonomy_level} launch_app requires approval: {needs}")

    # 6. Full pipeline guard: kill switch blocks, then report
    print("\n6. Reconciliation (dry) + Guardian status:")
    from core.safety_guardian import get_safety_guardian
    sg = get_safety_guardian()
    s = sg.get_status()
    print(f"   Guardian active_kills: {len(s['active_kills'])}, breakers: {len(s['circuit_breakers'])}")
    from actions.reconciliation import reconcile_30d
    rep = reconcile_30d(days=30, include_test=False)
    print(f"   Reconciliation verdict: {rep['verdict']}, audit valid: {rep['audit_integrity'].get('valid')}")

    # 7. Payment instruction generation (bank transfer - real FNB account)
    print("\n7. Payment Rails:")
    from actions.namibian_payments import handle as pay_handle
    bt = pay_handle({'action': 'create_payment', 'target': 'bank_transfer,99,NAD,DRY_PROD'})
    print(f"   Bank transfer link ok: {'instructions' in str(bt)}")

    print("\n=== PHASE 6 COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(test_phase6())
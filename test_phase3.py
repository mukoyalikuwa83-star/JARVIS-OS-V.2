"""Phase 3 verification: bounded autonomy, kill switch drills, circuit breakers, heartbeats."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_phase3():
    print("=== PHASE 3 VERIFICATION (BOUNDED AUTONOMY) ===")

    # 1. Safety guardian basics
    print("\n1. Safety Guardian:")
    from core.safety_guardian import (
        get_safety_guardian, trigger_kill, is_killed, KillLayer, KillReason,
        is_breaker_tripped, increment_scope, register_heartbeat, heartbeat
    )
    g = get_safety_guardian()
    status = g.get_status()
    print(f"   Breakers: {list(status['circuit_breakers'].keys())}")
    print(f"   any_active: {status['any_active']}")

    # 2. Kill switch drill
    print("\n2. Kill Switch Drill:")
    g.reset_circuit_breaker("scope_published_per_day", boss_confirmed=True)
    # Trigger a dry-run kill on a temporary domain
    trigger_kill(KillLayer.LOCAL_STOP, KillReason.MANUAL_LOCAL, "drill_domain",
                 {"drill": True, "note": "kill switch drill"})
    print(f"   Triggered kill on drill_domain")
    print(f"   is_killed(drill_domain): {is_killed('drill_domain')}")
    print(f"   is_killed(worker): {is_killed('worker')}")
    # Acknowledge the drill kill (Boss confirmation)
    g.acknowledge_domain_kills("drill_domain", boss_confirmed=True)
    print(f"   Acknowledged kill for drill_domain")
    print(f"   is_killed(drill_domain) after ack: {is_killed('drill_domain')}")

    # 3. Circuit breaker drill
    print("\n3. Circuit Breaker Drill:")
    # Force-push published counter past limit
    g.reset_circuit_breaker("scope_published_per_day", boss_confirmed=True)
    increment_scope("scope_published_per_day", 30)  # limit is 20
    print(f"   Scope published counter: {is_breaker_tripped('scope_published_per_day')} (tripped)")
    # Reset requires boss confirmation - test that
    try:
        g.reset_circuit_breaker("scope_published_per_day")
        print("   NOTE: Reset succeeded without boss_confirmed (unexpected)")
    except PermissionError as e:
        print(f"   Reset without boss confirmation blocked (ok): {str(e)[:50]}")
    g.reset_circuit_breaker("scope_published_per_day", boss_confirmed=True)
    print(f"   After boss-confirmed reset, tripped: {is_breaker_tripped('scope_published_per_day')}")

    # 4. Heartbeat
    print("\n4. Heartbeat (dead-man's switch):")
    g._heartbeats = {}
    register_heartbeat("worker", interval=60.0, max_missed=3)
    heartbeat("worker")
    g.check_heartbeats()
    k_status = g.get_status()
    print(f"   Heartbeats registered: {list(k_status['heartbeats'].keys())}")
    print(f"   is_killed(worker) after healthy heartbeat: {is_killed('worker')}")

    # 5. Bounded autonomy gating
    print("\n5. Bounded Autonomy Gating:")
    from actions.computer_control import ComputerControlAgent
    cc = ComputerControlAgent()
    # Level 1 = propose only
    can_exec, requires_approval, reason = cc.can_execute("launch_app")
    print(f"   Level {cc.config.autonomy_level} launch_app: can_execute={can_exec}, requires_approval={requires_approval}")
    # Always-approval action
    can_exec, requires_approval, reason = cc.can_execute("run_dangerous_command")
    print(f"   Always-approval run_dangerous_command: requires_approval={requires_approval}")
    # Raise to level 4 (within ceiling)
    cc.set_autonomy_level(4)
    can_exec, requires_approval, reason = cc.can_execute("launch_app")
    print(f"   Level 4 launch_app: can_execute={can_exec}, requires_approval={requires_approval}")
    # Cannot exceed ceiling
    try:
        cc.set_autonomy_level(9)
        print("   NOTE: set_autonomy_level(9) allowed (unexpected)")
    except ValueError as e:
        print(f"   Cannot exceed ceiling (ok): {str(e)[:50]}")

    # 6. Kill switch blocks the worker pipeline
    print("\n6. Kill Switch Blocks Pipeline:")
    from actions.autonomous_worker import AutonomousWorker
    from core.domain_registry import get_initialized_registry
    w = AutonomousWorker()
    # Simulate a kill on worker domain
    trigger_kill(KillLayer.LOCAL_STOP, KillReason.MANUAL_LOCAL, "worker", {"drill": True})
    result = w.full_pipeline()
    print(f"   Pipeline under kill: {result[:60]}")
    print(f"   BLOCKED by kill switch: {'BLOCKED BY KILL SWITCH' in result}")
    # Acknowledge to unfreeze
    g.acknowledge_domain_kills("worker", boss_confirmed=True)
    print(f"   is_killed(worker) after ack: {is_killed('worker')}")

    # 7. Recovery: worker heartbeat after pipeline
    print("\n7. Pipeline safe to run again (guardian heartbeat active):")
    heartbeat("worker")
    g.check_heartbeats()
    print(f"   is_killed(worker): {is_killed('worker')}")

    # 8. Drill cleanup: restore guardian to clean state
    print("\n8. Drill cleanup (no residue from this test):")
    for d in ["drill_domain", "worker", "content", "computer_control"]:
        g.acknowledge_domain_kills(d, boss_confirmed=True)
    for b in ["scope_published_per_day", "scope_accounts_per_day", "scope_messages_per_hour"]:
        try:
            g.reset_circuit_breaker(b, boss_confirmed=True)
        except Exception:
            pass
    final = g.get_status()
    print(f"   any_active: {final['any_active']}, active_kills: {len(final['active_kills'])}")
    assert not final["any_active"], "Kill switch should be clean after drill"

    print("\n=== PHASE 3 COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(test_phase3())
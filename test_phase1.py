import sys, os, asyncio
sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')
os.chdir(r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

async def test_phase1():
    print("=== PHASE 1 VERIFICATION ===\n")
    
    # 1. Core modules
    print("1. Core modules:")
    from actions._api import http_get, http_post, _load_env
    from core.gemini_compat import configure
    import core.tool_registry
    from core.safety_guardian import get_safety_guardian, trigger_kill, KillLayer, KillReason
    from core.audit_log import write_audit_entry, read_audit_log, get_audit_stats
    from core.credential_vault import get_vault, store_credential, get_credential
    from core.planner import get_planner
    from core.domain_agent import DomainRegistry, DomainConfig, DomainAgent
    from core.domain_registry import get_initialized_registry, get_all_domains, get_all_status
    print("   OK - All core modules import OK")
    
    # 2. Safety Guardian
    print("\n2. Safety Guardian:")
    sg = get_safety_guardian()
    print(f"   Status: {sg.get_status()}")
    
    # Test kill switch
    from core.safety_guardian import KillLayer, KillReason, get_safety_guardian
    sg = get_safety_guardian()
    sg.trigger_kill(KillLayer.LOCAL_STOP, KillReason.MANUAL_LOCAL, "test", {"test": True})
    status = sg.get_status()
    print(f"   Kill active: {status['any_active']}")
    print(f"   Active kills: {len(status['active_kills'])}")
    
    # Acknowledge
    if status['active_kills']:
        sg.acknowledge_domain_kills("test", boss_confirmed=True)
    
    # 3. Credential Vault
    print("\n3. Credential Vault:")
    from core.credential_vault import get_vault
    vault = get_vault()
    vault.store("test_key", "test_value", {"type": "test"})
    val = vault.get("test_key")
    print(f"   Store/Get: {val == 'test_value'}")
    
    # 4. Audit Log
    print("\n4. Audit Log:")
    from core.audit_log import write_audit_entry, get_audit_stats
    write_audit_entry(
        domain="test", action_proposed="test_action",
        screening_result="passed", gate_result="auto_approved:1",
        execution_result="success", real_outcome={"test": True},
        reasoning_summary="Test entry", credential_used="none"
    )
    stats = get_audit_stats()
    print(f"   Entries: {stats['total_entries']}")
    
    # 5. Planner
    print("\n5. Planner:")
    from core.planner import get_planner
    planner = get_planner()
    plan_id = await planner.create_plan("Build a CLI tool for log analysis")
    print(f"   Plan created: {plan_id}")
    plan = planner.get_plan(plan_id)
    print(f"   Steps: {len(plan['steps'])}")
    
    # 5. Domain Registry
    print("\n5. Domain Registry:")
    from core.domain_registry import DomainRegistry
    registry = DomainRegistry()
    print(f"   Registered domains: {list(registry.get_all().keys())}")
    
    # 6. Safety status
    print("\n6. Safety Status:")
    from core.safety_guardian import get_safety_status
    print(f"   {get_safety_status()}")
    
    print("\n=== PHASE 1 COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_phase1())
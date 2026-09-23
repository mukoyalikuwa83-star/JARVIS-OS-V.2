import sys, os, asyncio
sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')
os.chdir(r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

async def test_phase2():
    print("=== PHASE 2 VERIFICATION ===\n")
    
    # 1. Approval Gate
    print("1. Approval Gate:")
    from core.approval_gate import get_approval_gate, request_approval, get_pending_approvals, approve_request
    gate = get_approval_gate()
    print("   Approval gate initialized")
    
    # Submit a request
    result = await request_approval("computer_control", "delete_file", 
                                   {"path": "test.txt"}, 
                                   "Test deletion", 1)
    print(f"   Submit request (level 1): {result['status']}, requires_approval: {result['requires_approval']}")
    
    # Submit level 3 (auto-approved)
    result = await request_approval("computer_control", "create_file", 
                                   {"path": "test.txt", "content": "test"}, 
                                   "Test creation", 3)
    print(f"   Submit request (level 3): {result['status']}, requires_approval: {result['requires_approval']}")
    
    # Get pending
    pending = await get_pending_approvals()
    print(f"   Pending requests: {len(pending)}")
    
    # Approve
    if pending:
        req_id = pending[0]['request_id']
        result = await approve_request(req_id, "approve")
        print(f"   Approve request: {result['status']}")
    
    # 2. Sandbox Engine
    print("\n2. Sandbox Engine:")
    from actions.sandbox_trading import get_sandbox_engine, SandboxConfig, SandboxMode
    sandbox = get_sandbox_engine()
    
    # Create session
    config = SandboxConfig(mode=SandboxMode.PAPER, starting_capital=10000)
    session_id = await sandbox.create_session(config)
    print(f"   Session created: {session_id}")
    
    # Place order (0.005 BTC x ~$80k = $400, within 5% of $10k capital)
    result = await sandbox.place_order(session_id, "BTC", "long", 0.005)
    print(f"   Place order: {result.get('success')}, trade_id: {result.get('trade_id')}")
    
    # Close position
    result = await sandbox.close_position(session_id, "BTC")
    print(f"   Close position: {result.get('success')}, pnl: {result.get('pnl')}")
    
    # List sessions
    sessions = await sandbox.list_sessions()
    print(f"   Active sessions: {len(sessions)}")
    
    # 3. Domain Registry
    print("\n3. Domain Registry:")
    from core.domain_registry import get_initialized_registry, get_all_domains, get_all_status
    registry = get_initialized_registry()
    domains = get_all_domains()
    print(f"   Registered domains: {list(domains.keys())}")
    
    status = get_all_status()
    print(f"   Domain statuses: {list(status.keys())}")
    
    print("\n=== PHASE 2 COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_phase2())
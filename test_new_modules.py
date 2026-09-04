import sys
sys.path.insert(0, r"C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main")

results = []

try:
    from actions.camera_control import handle as h
    r = h({"action": "status"})
    results.append(f"camera_control: {r}")
except Exception as e:
    results.append(f"camera_control FAIL: {e}")

try:
    from actions.phone_tracking import handle as h
    r = h({"action": "status"})
    results.append(f"phone_tracking: {r}")
except Exception as e:
    results.append(f"phone_tracking FAIL: {e}")

try:
    from actions.smart_home import handle as h
    r = h({"action": "status"})
    results.append(f"smart_home: {r}")
except Exception as e:
    results.append(f"smart_home FAIL: {e}")

try:
    from actions.vehicle_control import handle as h
    r = h({"action": "status"})
    results.append(f"vehicle_control: {r}")
except Exception as e:
    results.append(f"vehicle_control FAIL: {e}")

try:
    from actions.cybersecurity import handle as h
    r = h({"action": "status"})
    results.append(f"cybersecurity: {r}")
except Exception as e:
    results.append(f"cybersecurity FAIL: {e}")

try:
    from actions.data_analysis import handle as h
    r = h({"action": "status"})
    results.append(f"data_analysis: {r}")
except Exception as e:
    results.append(f"data_analysis FAIL: {e}")

try:
    from actions.automation_engine import handle as h
    r = h({"action": "status"})
    results.append(f"automation_engine: {r}")
except Exception as e:
    results.append(f"automation_engine FAIL: {e}")

try:
    from memory.persistent_memory import log_conversation, build_memory_context
    log_conversation("test user msg", "test jarvis reply")
    ctx = build_memory_context()
    results.append(f"persistent_memory: OK ({len(ctx)} chars)")
except Exception as e:
    results.append(f"persistent_memory FAIL: {e}")

for r in results:
    print(r)

print(f"\nTotal: {len(results)} modules tested")

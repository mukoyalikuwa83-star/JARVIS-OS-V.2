import sys
sys.path.insert(0, r"C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main")

# Test non-camera modules only (camera blocks on OpenCV)
tests = [
    ("phone_tracking", "from actions.phone_tracking import handle; print(handle({'action':'status'}))"),
    ("smart_home", "from actions.smart_home import handle; print(handle({'action':'status'}))"),
    ("vehicle_control", "from actions.vehicle_control import handle; print(handle({'action':'status'}))"),
    ("cybersecurity", "from actions.cybersecurity import handle; print(handle({'action':'status'}))"),
    ("data_analysis", "from actions.data_analysis import handle; print(handle({'action':'status'}))"),
    ("automation_engine", "from actions.automation_engine import handle; print(handle({'action':'status'}))"),
    ("stripe_payments", "from actions.stripe_payments import handle; print(handle({'action':'status'}))"),
    ("persistent_memory", "from memory.persistent_memory import log_conversation, build_memory_context; log_conversation('test','reply'); print('OK:', len(build_memory_context()), 'chars')"),
]

for name, code in tests:
    try:
        exec(code)
        print(f"  {name}: PASS")
    except Exception as e:
        print(f"  {name}: FAIL - {e}")

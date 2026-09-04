import sys, re
sys.path.insert(0, r"C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main")

print("=== JARVIS-OS FINAL VERIFICATION ===\n")

# 1. Count tools
content = open("main.py", "r", encoding="utf-8").read()
start = content.find("TOOL_DECLARATIONS = [")
bracket_count = 0
end = start
for i, ch in enumerate(content[start:], start):
    if ch == '[': bracket_count += 1
    elif ch == ']':
        bracket_count -= 1
        if bracket_count == 0:
            end = i + 1
            break
block = content[start:end]
tools = re.findall(r'"name":\s*"(\w+)"', block)
print(f"1. Tool declarations: {len(tools)}")

# 2. Count dispatch entries
dispatch_count = content.count('elif name == "') + content.count('if name == "')
print(f"2. Dispatch entries: {dispatch_count}")

# 3. Test all new modules
modules = [
    "actions.phone_tracking",
    "actions.smart_home",
    "actions.vehicle_control",
    "actions.cybersecurity",
    "actions.data_analysis",
    "actions.automation_engine",
    "actions.stripe_payments",
    "memory.persistent_memory",
]
passed = 0
for mod in modules:
    try:
        m = __import__(mod, fromlist=["handle"])
        r = m.handle({"action": "status"})
        passed += 1
    except Exception as e:
        print(f"   FAIL: {mod} - {e}")
print(f"3. Module tests: {passed}/{len(modules)} passed")

# 4. Check API keys
import os
from pathlib import Path
env_path = Path("C:/Users/2025/OneDrive/Desktop/JARVIS-OS-V.2-main/JARVIS-OS-V.2-main/.env")
env = env_path.read_text(encoding="utf-8")
keys = {
    "GEMINI_API_KEY": "GEMINI_API_KEY=" in env,
    "STRIPE_PUBLISHABLE": "STRIPE_PUBLISHABLE_KEY=" in env,
    "STRIPE_SECRET": "STRIPE_SECRET_KEY=" in env,
    "GUMROAD_ACCESS_TOKEN": "GUMROAD_ACCESS_TOKEN=" in env,
    "GUMROAD_APP_ID": "GUMROAD_APP_ID=" in env,
    "GUMROAD_APP_SECRET": "GUMROAD_APP_SECRET=" in env,
}
set_count = sum(1 for v in keys.values() if v)
print(f"4. API keys configured: {set_count}/{len(keys)}")

# 5. Check accounts.json
acc_path = Path("C:/Users/2025/OneDrive/Desktop/JARVIS-OS-V.2-main/JARVIS-OS-V.2-main/.jarvis/accounts.json")
import json
acc = json.loads(acc_path.read_text(encoding="utf-8"))
accounts = list(acc.keys())
print(f"5. Accounts stored: {accounts}")

# 6. Check persistent memory
from memory.persistent_memory import log_conversation, build_memory_context, get_conversation_stats
stats = get_conversation_stats()
print(f"6. Persistent memory: {stats}")

# 7. Check __init__.py files
init_dirs = ["actions", "core", "memory", "awareness", "agent", "api"]
init_ok = sum(1 for d in init_dirs if (Path(d) / "__init__.py").exists())
print(f"7. Package init files: {init_ok}/{len(init_dirs)}")

# 8. Check product count
products_dir = Path(".jarvis/products")
zips = list(products_dir.glob("*.zip")) if products_dir.exists() else []
print(f"8. Product ZIPs: {len(zips)}")

# 9. Check main.py line count
lines = content.count("\n") + 1
print(f"9. main.py lines: {lines}")

# 10. Latency settings
vad = re.search(r"LIVE_VAD_SILENCE_MS\s*=\s*(\d+)", content)
barge = re.search(r"self\._barge_in_grace_ms\s*=\s*([\d.]+)", content)
gain = re.search(r"_MIC_GAIN_DB\s*=\s*(\d+)", content)
print(f"10. Latency: VAD={vad.group(1)}ms, Barge-in={barge.group(1)}s, Mic gain={gain.group(1)}dB")

print("\n=== ALL CHECKS COMPLETE ===")

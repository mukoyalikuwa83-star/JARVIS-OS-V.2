"""Test all JARVIS action modules and tool connections."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("JARVIS_AUTO_START", "1")

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "OK"))
        print(f"  [OK] {name}")
    except Exception as e:
        results.append((name, f"FAIL: {e}"))
        print(f"  [FAIL] {name}: {e}")

print("=== Testing Action Module Imports ===")

test("autonomous_worker", lambda: __import__("actions.autonomous_worker"))
test("gumroad_api", lambda: __import__("actions.gumroad_api"))
test("social_media", lambda: __import__("actions.social_media"))
test("content_engine", lambda: __import__("actions.content_engine"))
test("product_enricher", lambda: __import__("actions.product_enricher"))
test("money_makers", lambda: __import__("actions.money_makers"))
test("self_evolution", lambda: __import__("actions.self_evolution"))
test("tts_engine", lambda: __import__("actions.tts_engine"))
test("noise_filter", lambda: __import__("actions.noise_filter"))
test("account_manager", lambda: __import__("actions.account_manager"))
test("email_control", lambda: __import__("actions.email_control"))
test("send_message", lambda: __import__("actions.send_message"))
test("screen_automation", lambda: __import__("actions.screen_automation"))
test("computer_settings", lambda: __import__("actions.computer_settings"))
test("system_access", lambda: __import__("actions.system_access"))
test("browser_control", lambda: __import__("actions.browser_control"))
test("mood_detector", lambda: __import__("actions.mood_detector"))
test("autonomous_brain", lambda: __import__("actions.autonomous_brain"))
test("screen_processor", lambda: __import__("actions.screen_processor"))
test("instagram_browser", lambda: __import__("actions.instagram_browser"))
test("safe_text_entry", lambda: __import__("actions.safe_text_entry"))
test("jarvis_file_stamp", lambda: __import__("actions.jarvis_file_stamp"))

print("\n=== Testing Core Imports ===")

def t_genai():
    from google import genai
    print(f"    genai version: {genai.__version__}")
test("google.genai", t_genai)

def t_pydantic():
    import pydantic
    print(f"    pydantic version: {pydantic.__version__}")
test("pydantic", t_pydantic)

test("numpy", lambda: __import__("numpy"))
test("sounddevice", lambda: __import__("sounddevice"))
test("soundfile", lambda: __import__("soundfile"))
test("pillow", lambda: __import__("PIL"))
test("pyautogui", lambda: __import__("pyautogui"))
test("requests", lambda: __import__("requests"))
test("websockets", lambda: __import__("websockets"))

print("\n=== Testing Tool Declaration Count ===")
def t_tool_count():
    import ast
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TOOL_DECLARATIONS":
                    if isinstance(node.value, ast.List):
                        count = len(node.value.elts)
                        print(f"    TOOL_DECLARATIONS has {count} tools")
                        assert count >= 60, f"Expected 68 tools, got {count}"
test("tool_declaration_count", t_tool_count)

print("\n=== Testing TTS Volume Setting ===")
def t_tts_volume():
    from actions.tts_engine import _TTS_VOLUME_MULTIPLIER
    print(f"    TTS volume multiplier: {_TTS_VOLUME_MULTIPLIER}x")
    assert _TTS_VOLUME_MULTIPLIER >= 2.0, f"Volume too low: {_TTS_VOLUME_MULTIPLIER}"
test("tts_volume", t_tts_volume)

print("\n=== Testing Mic Settings ===")
def t_mic_settings():
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "_MIC_GAIN_DB = 80" in content, "Mic gain not updated"
    assert "_MIC_NOISE_GATE_THRESHOLD = 1" in content, "Noise gate not updated"
    assert "_MIC_AGC_TARGET = 12000" in content, "AGC target not updated"
    print("    Mic gain: 80dB, Noise gate: 1, AGC target: 12000")
test("mic_settings", t_mic_settings)

print("\n=== Testing Dispatch Connections ===")
def t_dispatch():
    import ast
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_ACTION_MODULES":
                    if isinstance(node.value, ast.Dict):
                        count = len(node.value.keys)
                        print(f"    _ACTION_MODULES has {count} entries")
                        assert count >= 20, f"Expected 20+ dispatch entries, got {count}"
test("dispatch_connections", t_dispatch)

print("\n" + "=" * 50)
ok = sum(1 for _, s in results if s == "OK")
fail = sum(1 for _, s in results if s != "OK")
print(f"Results: {ok} passed, {fail} failed out of {len(results)} total")
if fail:
    print("\nFailed tests:")
    for name, status in results:
        if status != "OK":
            print(f"  - {name}: {status}")
else:
    print("\nALL TESTS PASSED!")

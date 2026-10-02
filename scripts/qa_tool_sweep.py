"""Exhaustive tool-execution sweep for JARVIS.

Boots a stubbed JarvisLive and calls every declared tool through the REAL
dispatcher (JarvisLive._execute_tool) with side-effect-safe arguments.

Classes side effects are prevented by:
  * pass1  -> universally-bogus action "__qa_probe__" (handlers answer with a
              help/unknown message instead of doing anything)
  * pass2  -> curated read-only action per tool
  * skip   -> tools whose every path has external side effects (screen_process,
              check_messages) are contract-verified only (import + callable)

Never triggers: messaging, email, payments, posts, camera capture, screen
upload, agent execution, desktop automation code execution.

Run:
    .venv\\Scripts\\python.exe scripts\\qa_tool_sweep.py
"""

import asyncio
import importlib
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CALL_TIMEOUT = 90.0          # seconds per tool call
TRUNCATE = 160               # chars of result text kept in the report
PROBE = "__qa_probe__"

FAIL_PREFIXES = ("Unknown tool:",)
FAIL_SUBSTRINGS = ("failed:",)


# --------------------------------------------------------------------------
# stubs
# --------------------------------------------------------------------------

class StubUI:
    def __init__(self):
        self.muted = False
        self.operational_ready = True
        self.on_text_command = None
        self.current_file = None
        self.logs = []
        self.subtitles = []
        self.states = []
        self.mic_states = []
        self.theme = "arc_reactor"
        self.graphics = "high"

    def write_log(self, text):
        self.logs.append(text)

    def set_state(self, state):
        self.states.append(state)

    def set_mic_state(self, state):
        self.mic_states.append(state)

    def show_subtitle(self, _text, _dur=None):
        self.subtitles.append(_text)

    def clear_subtitle(self):
        self.subtitles.append(None)

    def handle_ui_command(self, *_a, **_k):
        return None

    def set_theme(self, name):
        self.theme = name

    def set_graphics_quality(self, name):
        self.graphics = name

    def sync_voice_display(self):
        return None


_FAKE_QUEUE_SUBMISSIONS = []


class _FakeQueue:
    """Mirrors agent.task_queue.TaskQueue's read-only surface faithfully.

    Never spawns threads; records submissions so task_status can report them.
    """

    def submit(self, goal="", priority="normal", speak=None, immediate=False):
        prio = priority if isinstance(priority, str) else getattr(priority, "value", str(priority))
        _FAKE_QUEUE_SUBMISSIONS.append(
            {"task_id": "qa-sweep", "goal": str(goal)[:50], "priority": prio, "immediate": immediate})
        return "qa-sweep"

    def get_status(self, task_id):
        for s in _FAKE_QUEUE_SUBMISSIONS:
            if s["task_id"] == task_id:
                return {"task_id": s["task_id"], "goal": s["goal"], "status": "queued",
                        "result": None, "error": None, "kind": "agent", "progress": 0,
                        "phase": "Queued", "artifacts": [], "warnings": []}
        return None

    def get_all_statuses(self):
        return [{"task_id": s["task_id"], "goal": s["goal"], "status": "queued",
                 "kind": "agent", "progress": 0, "phase": "Queued"}
                for s in _FAKE_QUEUE_SUBMISSIONS]

    def cancel(self, task_id):
        return any(s["task_id"] == task_id for s in _FAKE_QUEUE_SUBMISSIONS)


def install_stubs(jarvis_main):
    """Patch every outbound side effect the dispatcher can reach."""
    ui = StubUI()

    jarvis = jarvis_main.JarvisLive(ui, jarvis_main._load_voice_name())

    jarvis.speak = lambda *_a, **_k: None
    jarvis.speak_error = lambda *_a, **_k: None
    jarvis._safe_send_content_sync = lambda *_a, **_k: None
    jarvis._speak_vision_result = lambda *_a, **_k: False
    jarvis._intercept_ui_tool_call = lambda *_a, **_k: None

    # agent task queue: record submissions instead of executing agents
    try:
        import agent.task_queue as task_queue_mod
        task_queue_mod.get_queue = lambda *_a, **_k: _FakeQueue()
    except Exception:
        pass

    # learning memory write-behind: silence
    try:
        import actions.learning_memory as lm
        lm.track_pattern = lambda *_a, **_k: None
        lm.set_context = lambda *_a, **_k: None
    except Exception:
        pass

    # answer cache writes during post-processing
    try:
        import actions.web_search_cache as cache_mod
        if hasattr(cache_mod, "save_cached_answer"):
            cache_mod.save_cached_answer = lambda *_a, **_k: None
    except Exception:
        pass

    return jarvis, ui


# --------------------------------------------------------------------------
# sweep matrix
# --------------------------------------------------------------------------

# tools that are contract-verified only (no safe execution path)
SKIP_EXEC = {
    "screen_process": "captures/uploads screen content",
    "check_messages": "reads private conversations (Instagram DM / iMessage)",
}

# curated read-only pass2 per tool
PASS2 = {
    "open_app": {},
    "weather_report": {},
    "email_control": {"action": "status"},
    "bluetooth_control": {"action": "status"},
    "wifi_control": {"action": "status"},
    "calendar_control": {"action": "list"},
    "autonomous_control": {"action": "status"},
    "market_monitor": {"action": "watchlist"},
    "daily_briefing": {"action": "weather"},
    "contact_manager": {"action": "list"},
    "taskbar_detect": {"action": "running_list"},
    "full_control": {"action": "system_info_full"},
    "cybersec": {"action": "network_info"},
    "screen_auto": {"action": "get_screen_size"},
    "monitor": {"action": "get_status"},
    "cleanup": {"action": "memory_status"},
    "proactive_tasks": {"action": "list"},
    "learning_memory": {"action": "list_prefs"},
    "alarm_timer": {"action": "list_timers"},
    "system_access": {"action": "get_battery_status"},
    "self_control": {"action": "get_status"},
    "autonomous_brain": {"action": "status"},
    "money_makers": {"action": "portfolio_status"},
    "gumroad_api": {"action": "status"},
    "social_media": {"action": "status"},
    "content_engine": {"action": "status"},
    "self_evolution": {"action": "status"},
    "auto_start": {"action": "status"},
    "autonomous_worker": {"action": "status"},
    "mood_status": {"action": "summary"},
    "screen_awareness": {"action": "should_read"},
    "real_hustle": {"action": "status"},
    "smart_home": {"action": "status"},
    "phone_tracking": {"action": "call_stats"},
    "vehicle_control": {"action": "status"},
    "cybersecurity": {"action": "status"},
    "automation_engine": {"action": "list"},
    "stripe_payments": {"action": "status"},
    "game_updater": {"action": "list"},
    "camera_control": {"action": "stop_video"},
    "computer_control": {"action": "user_data"},
    "task_status": {"action": "all"},
    "system_info": {"action": "all"},
    "jarvis_ui_control": {"action": "change_theme", "theme": "arc_reactor"},
    "safe_text_entry": {"action": "validate"},
    "notification_center": {"action": "get"},
    "desktop_control": {"action": "stats"},
}

# extra read-only pass3 for desktop_control (its unknown-action path is DANGEROUS:
# it feeds the action to an LLM and executes generated desktop code)
PASS3 = {
    "desktop_control": {"action": "current_wallpaper"},
}

# pass1 action style: tools whose pass1 should use the generic bogus probe
PASS1_BOGUS = True


def tool_names():
    from core.tool_registry import TOOL_DECLARATIONS
    names = []
    for decl in TOOL_DECLARATIONS:
        try:
            names.append(decl["name"] if isinstance(decl, dict) else decl.name)
        except Exception:
            names.append(str(decl))
    return names


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------

def classify(name, result_text, exc, hung):
    if hung:
        return "HANG", result_text
    if exc is not None:
        return "FAIL", f"sweep exception: {exc.__class__.__name__}: {exc}"
    text = result_text if isinstance(result_text, str) else ""
    if text.startswith("Unknown tool:"):
        return "FAIL", text
    # dispatcher exception path: f"Tool '{name}' failed: {e}"
    if text.startswith(("Tool '", "Tool \u2018")) and "failed:" in text[:400]:
        return "FAIL", text
    return "OK", text


def describe(result):
    """Extract the payload from a types.FunctionResponse (response={'result': ...})."""
    payload = getattr(result, "response", None)
    if isinstance(payload, dict) and "result" in payload:
        result = payload["result"]
    if isinstance(result, str):
        return result
    try:
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result)
    except Exception:
        return repr(result)


class _FakeFunctionCall:
    """Minimal stand-in for types.FunctionCall (dispatcher reads .name/.args/.id)."""

    def __init__(self, name, args):
        self.name = name
        self.args = args
        self.id = f"sweep-{name}"


async def call_tool(jarvis, name, args):
    return await jarvis._execute_tool(_FakeFunctionCall(name, args))


def run_one(jarvis, name, args):
    """Execute a single tool call in a worker thread with a timeout."""
    box = {"result": None, "exc": None, "done": False}

    def worker():
        try:
            box["result"] = asyncio.run(call_tool(jarvis, name, args))
        except BaseException as e:  # noqa: BLE001
            box["exc"] = e
        finally:
            box["done"] = True

    t = threading.Thread(target=worker, name=f"sweep-{name}", daemon=True)
    t.start()
    t.join(CALL_TIMEOUT)
    hung = not box["done"]
    return box["result"], box["exc"], hung


def main():
    report_dir = BASE_DIR / ".qa-artifacts" / f"tool-sweep-{datetime.now():%Y%m%d-%H%M%S}"
    report_dir.mkdir(parents=True, exist_ok=True)

    import main as jarvis_main
    jarvis, ui = install_stubs(jarvis_main)

    # qa_mode must stay OFF for the sweep to exercise real dispatch
    if os.environ.get("JARVIS_QA_MODE"):
        del os.environ["JARVIS_QA_MODE"]

    names = tool_names()
    print(f"Tool sweep: {len(names)} declared tools, timeout {CALL_TIMEOUT}s/call")
    print(f"Artifacts: {report_dir}")
    print("-" * 72)

    records = []
    for i, name in enumerate(names, 1):
        record = {"name": name, "calls": []}

        if name in SKIP_EXEC:
            try:
                cls = getattr(jarvis_main, "JarvisLive", None)
                ok = callable(getattr(cls, "_execute_tool", None))
                record["skip_reason"] = SKIP_EXEC[name]
                record["status"] = "SKIP" if ok else "FAIL"
                record["detail"] = ("contract-verified: dispatcher callable"
                                    if ok else "dispatcher missing")
            except Exception as e:  # noqa: BLE001
                record["status"] = "FAIL"
                record["detail"] = f"contract verify failed: {e}"
            records.append(record)
            print(f"[{i:02d}/{len(names)}] {name:<24} SKIP  ({SKIP_EXEC[name]})")
            continue

        calls = []
        if name not in SKIP_EXEC:
            if name == "desktop_control":
                pass  # never send bogus action to desktop_control
            else:
                calls.append({"action": PROBE})
        if name in PASS2:
            calls.append(PASS2[name])
        if name in PASS3:
            calls.append(PASS3[name])

        statuses = []
        for args in calls:
            args = dict(args)
            started = time.time()
            result, exc, hung = run_one(jarvis, name, args)
            elapsed = time.time() - started
            text = describe(result)[:TRUNCATE] if result is not None else ""
            verdict, detail = classify(name, text, exc, hung)
            record["calls"].append({
                "args": args,
                "status": verdict,
                "elapsed": round(elapsed, 2),
                "detail": detail,
            })
            statuses.append(verdict)
            print(f"[{i:02d}/{len(names)}] {name:<24} {verdict:<4} "
                  f"{elapsed:6.2f}s  {detail[:90]!r}" if detail else
                  f"[{i:02d}/{len(names)}] {name:<24} {verdict:<4} {elapsed:6.2f}s")

        if "HANG" in statuses:
            record["status"] = "HANG"
        elif "FAIL" in statuses:
            record["status"] = "FAIL"
        else:
            record["status"] = "OK"
        records.append(record)

    # ------------------------------------------------------------------
    summary = {
        "timestamp": datetime.now().isoformat(),
        "declared": len(names),
        "ok": sum(1 for r in records if r["status"] == "OK"),
        "skip": sum(1 for r in records if r["status"] == "SKIP"),
        "fail": sum(1 for r in records if r["status"] == "FAIL"),
        "hang": sum(1 for r in records if r["status"] == "HANG"),
        "records": records,
    }
    out = report_dir / "results.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 72)
    print(f"OK={summary['ok']}  SKIP={summary['skip']}  "
          f"FAIL={summary['fail']}  HANG={summary['hang']}  "
          f"(of {summary['declared']})")
    print(f"results: {out}")

    failures = [r for r in records if r["status"] in ("FAIL", "HANG")]
    if failures:
        print("\nFailures:")
        for r in failures:
            for call in r.get("calls", []):
                if call["status"] in ("FAIL", "HANG"):
                    print(f"  - {r['name']} {call['args']}: {call['detail']}")
            if not r.get("calls"):
                print(f"  - {r['name']}: {r.get('detail')}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

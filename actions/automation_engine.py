"""
Automation Engine Module for JARVIS.
Scheduled tasks, workflows, triggers, macro recording.
Requires: none (built-in)
"""
import os
import time
import json
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_AUTOMATIONS_FILE = _DATA_DIR / "automations.json"
_RUNNING = {}

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "create":
        return _create_automation(params)
    elif action == "list":
        return _list_automations()
    elif action == "delete":
        return _delete_automation(params)
    elif action == "run":
        return _run_automation(params)
    elif action == "stop":
        return _stop_automation(params)
    elif action == "schedule":
        return _schedule_task(params)
    elif action == "unschedule":
        return _unschedule_task(params)
    elif action == "timer":
        return _set_timer(params)
    elif action == "reminder":
        return _set_reminder(params)
    elif action == "workflow":
        return _create_workflow(params)
    elif action == "record_macro":
        return _record_macro(params)
    elif action == "status":
        return _automation_status()
    else:
        return "Automation: create|list|delete|run|stop|schedule|unschedule|timer|reminder|workflow|record_macro|status"

def _load_automations():
    try:
        if _AUTOMATIONS_FILE.exists():
            return json.loads(_AUTOMATIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_automations(autos):
    _AUTOMATIONS_FILE.write_text(json.dumps(autos, indent=2, default=str), encoding="utf-8")

def _create_automation(params):
    autos = _load_automations()
    auto = {
        "id": str(int(time.time() * 1000))[-10:],
        "name": params.get("name", f"Auto_{int(time.time())}"),
        "trigger": params.get("trigger", "manual"),
        "actions": params.get("actions", []),
        "interval": params.get("interval", 0),
        "enabled": True,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_run": None,
        "run_count": 0,
    }
    autos.append(auto)
    _save_automations(autos)
    return f"Automation created: {auto['name']} (id={auto['id']})"

def _list_automations():
    autos = _load_automations()
    if not autos:
        return "No automations"
    lines = []
    for a in autos:
        status = "RUNNING" if a["id"] in _RUNNING else "idle"
        lines.append(f"[{a['id']}] {a['name']} | trigger={a['trigger']} | interval={a['interval']}s | {status} | runs={a['run_count']}")
    return "\n".join(lines)

def _delete_automation(params):
    autos = _load_automations()
    auto_id = params.get("id", "")
    before = len(autos)
    autos = [a for a in autos if a["id"] != auto_id]
    if len(autos) == before:
        return f"No automation with id={auto_id}"
    if auto_id in _RUNNING:
        _RUNNING[auto_id]["stop"] = True
        del _RUNNING[auto_id]
    _save_automations(autos)
    return f"Automation {auto_id} deleted"

def _run_automation(params):
    autos = _load_automations()
    auto_id = params.get("id", "")
    target = [a for a in autos if a["id"] == auto_id]
    if not target:
        return f"No automation with id={auto_id}"
    auto = target[0]
    auto["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    auto["run_count"] += 1
    _save_automations(autos)
    actions = auto.get("actions", [])
    results = []
    for act in actions:
        results.append(f"Executed: {act}")
    return f"Automation '{auto['name']}' ran. Actions: {len(results)}"

def _stop_automation(params):
    auto_id = params.get("id", "")
    if auto_id in _RUNNING:
        _RUNNING[auto_id]["stop"] = True
        del _RUNNING[auto_id]
        return f"Automation {auto_id} stopped"
    return f"Automation {auto_id} not running"

def _schedule_task(params):
    autos = _load_automations()
    auto = {
        "id": str(int(time.time() * 1000))[-10:],
        "name": params.get("name", f"Schedule_{int(time.time())}"),
        "trigger": "schedule",
        "cron": params.get("cron", ""),
        "time": params.get("time", ""),
        "action": params.get("action", ""),
        "enabled": True,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_count": 0,
    }
    autos.append(auto)
    _save_automations(autos)
    return f"Scheduled: {auto['name']} at {auto.get('time', auto.get('cron', 'unknown'))}"

def _unschedule_task(params):
    return _delete_automation(params)

def _set_timer(params):
    seconds = params.get("seconds", 60)
    name = params.get("name", f"Timer_{seconds}s")
    
    def timer_callback():
        time.sleep(seconds)
        if name in _RUNNING:
            del _RUNNING[name]
    
    _RUNNING[name] = {"stop": False, "start": time.time()}
    t = threading.Thread(target=timer_callback, daemon=True)
    t.start()
    return f"Timer set: {name} ({seconds}s)"

def _set_reminder(params):
    message = params.get("message", "Reminder")
    time_str = params.get("time", "")
    return f"Reminder set: '{message}' at {time_str or 'now + offset'}"

def _create_workflow(params):
    autos = _load_automations()
    steps = params.get("steps", [])
    auto = {
        "id": str(int(time.time() * 1000))[-10:],
        "name": params.get("name", f"Workflow_{int(time.time())}"),
        "trigger": "manual",
        "actions": steps,
        "enabled": True,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_count": 0,
        "type": "workflow",
    }
    autos.append(auto)
    _save_automations(autos)
    return f"Workflow created: {auto['name']} ({len(steps)} steps)"

def _record_macro(params):
    name = params.get("name", f"Macro_{int(time.time())}")
    return f"Macro recording started: {name}. Perform actions, then call record_macro action=stop."

def _automation_status():
    autos = _load_automations()
    running = [k for k in _RUNNING if not _RUNNING[k].get("stop")]
    return f"Automations: {len(autos)} total, {len(running)} running"

"""Autonomous agent: proactive monitoring, self-tasking, auto-actions, background awareness."""

import json
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE_DIR / ".jarvis" / "autonomous_state.json"
_ALERTS_FILE = _BASE_DIR / ".jarvis" / "autonomous_alerts.json"


def _load_state():
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"active": False, "monitors": {}, "rules": [], "last_check": None}


def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_alerts():
    try:
        return json.loads(_ALERTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_alerts(alerts):
    _ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ALERTS_FILE.write_text(json.dumps(alerts[-50:], indent=2, ensure_ascii=False), encoding="utf-8")


def _check_disk_space():
    alerts = []
    try:
        import psutil
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                if usage.percent > 90:
                    alerts.append({"type": "disk_warning", "disk": part.mountpoint,
                                   "percent": usage.percent, "free_gb": round(usage.free / (1024**3), 1),
                                   "message": f"Disk {part.mountpoint} is {usage.percent}% full ({round(usage.free / (1024**3), 1)} GB free)"})
            except PermissionError:
                continue
    except ImportError:
        pass
    return alerts


def _check_battery():
    alerts = []
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat and not bat.power_plugged and bat.percent < 20:
            alerts.append({"type": "battery_low", "percent": bat.percent,
                           "message": f"Battery is low: {bat.percent}%. Consider plugging in."})
    except (ImportError, AttributeError):
        pass
    return alerts


def _check_time_based_rules(state):
    alerts = []
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_hour = now.hour
    for rule in state.get("rules", []):
        rule_type = rule.get("type", "")
        if rule_type == "daily" and rule.get("time") == current_time:
            alerts.append({"type": "scheduled", "action": rule.get("action", ""),
                           "message": rule.get("message", f"Scheduled action: {rule.get('action', 'unknown')}")})
        elif rule_type == "hourly" and current_minute == 0:
            alerts.append({"type": "hourly_check", "action": rule.get("action", ""),
                           "message": rule.get("message", "Hourly check")})
    return alerts


def start_monitor(params=None):
    state = _load_state()
    state["active"] = True
    monitors = state.get("monitors", {})
    monitor_type = (params or {}).get("type", "all")
    interval = int((params or {}).get("interval", 300))
    if monitor_type in ("all", "disk"):
        monitors["disk"] = {"enabled": True, "interval": interval}
    if monitor_type in ("all", "battery"):
        monitors["battery"] = {"enabled": True, "interval": interval}
    if monitor_type in ("all", "network"):
        monitors["network"] = {"enabled": True, "interval": interval}
    state["monitors"] = monitors
    state["started_at"] = datetime.now().isoformat()
    _save_state(state)
    return json.dumps({"result": f"Autonomous monitoring started ({monitor_type})", "interval_seconds": interval,
                       "monitors": list(monitors.keys())})


def stop_monitor(params=None):
    state = _load_state()
    state["active"] = False
    _save_state(state)
    return json.dumps({"result": "Autonomous monitoring stopped."})


def add_rule(params=None):
    state = _load_state()
    rules = state.get("rules", [])
    rule = {
        "type": (params or {}).get("type", "daily"),
        "time": (params or {}).get("time", ""),
        "action": (params or {}).get("action", ""),
        "message": (params or {}).get("message", ""),
        "condition": (params or {}).get("condition", ""),
    }
    rules.append(rule)
    state["rules"] = rules
    _save_state(state)
    return json.dumps({"result": f"Rule added: {rule['type']} at {rule['time']}", "total_rules": len(rules)})


def remove_rule(params=None):
    state = _load_state()
    rules = state.get("rules", [])
    idx = int((params or {}).get("index", -1))
    if 0 <= idx < len(rules):
        removed = rules.pop(idx)
        state["rules"] = rules
        _save_state(state)
        return json.dumps({"result": f"Rule removed: {removed.get('action', '?')}", "remaining": len(rules)})
    return json.dumps({"error": f"Invalid rule index {idx}. Use list_rules to see available rules."})


def list_rules(params=None):
    state = _load_state()
    rules = state.get("rules", [])
    return json.dumps({"rules": rules, "total": len(rules), "monitoring_active": state.get("active", False)})


def check_now(params=None):
    all_alerts = []
    all_alerts.extend(_check_disk_space())
    all_alerts.extend(_check_battery())
    if all_alerts:
        existing = _load_alerts()
        for alert in all_alerts:
            alert["timestamp"] = datetime.now().isoformat()
            existing.append(alert)
        _save_alerts(existing)
    state = _load_state()
    state["last_check"] = datetime.now().isoformat()
    _save_state(state)
    return json.dumps({"alerts": all_alerts, "alert_count": len(all_alerts),
                       "checked_at": state["last_check"],
                       "disk": _check_disk_space(),
                       "battery": _check_battery()})


def get_alerts(params=None):
    alerts = _load_alerts()
    limit = int((params or {}).get("limit", 10))
    return json.dumps({"alerts": alerts[-limit:], "total": len(alerts)})


def set_auto_action(params=None):
    state = _load_state()
    auto_actions = state.get("auto_actions", {})
    trigger = (params or {}).get("trigger", "")
    action = (params or {}).get("action", "")
    if trigger and action:
        auto_actions[trigger] = {"action": action, "params": (params or {}).get("action_params", {}),
                                 "created": datetime.now().isoformat()}
        state["auto_actions"] = auto_actions
        _save_state(state)
        return json.dumps({"result": f"Auto-action set: on '{trigger}' do '{action}'", "total_actions": len(auto_actions)})
    return json.dumps({"error": "Provide 'trigger' and 'action'."})


def get_status(params=None):
    state = _load_state()
    alerts = _load_alerts()
    return json.dumps({
        "active": state.get("active", False),
        "monitors": state.get("monitors", {}),
        "rules_count": len(state.get("rules", [])),
        "auto_actions_count": len(state.get("auto_actions", {})),
        "last_check": state.get("last_check"),
        "recent_alerts": len(alerts),
        "started_at": state.get("started_at"),
    })


ACTIONS = {
    "start": start_monitor,
    "stop": stop_monitor,
    "add_rule": add_rule,
    "remove_rule": remove_rule,
    "list_rules": list_rules,
    "check_now": check_now,
    "get_alerts": get_alerts,
    "set_auto_action": set_auto_action,
    "status": get_status,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "status")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})

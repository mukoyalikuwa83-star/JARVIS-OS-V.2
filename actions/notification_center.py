"""Notification center — queue alerts, schedule reminders, manage notification history."""

import json
import time
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / ".jarvis"
_NOTIF_FILE = _MEMORY_DIR / "notifications.json"
_SCHEDULE_FILE = _MEMORY_DIR / "scheduled_alerts.json"


def _load_json(path: Path) -> list | dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [] if "notif" in path.name else {}


def _save_json(path: Path, data):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def push_notification(params: dict) -> str:
    """Push a notification to the center."""
    title = str(params.get("title", "") or "").strip()
    message = str(params.get("message", "") or "").strip()
    level = str(params.get("level", "info") or "info").strip().lower()
    source = str(params.get("source", "system") or "system").strip()

    if not title and not message:
        return "ERROR: Provide title or message."

    notifs = _load_json(_NOTIF_FILE)
    if not isinstance(notifs, list):
        notifs = []

    notif = {
        "id": f"n_{int(time.time())}",
        "title": title or "Notification",
        "message": message,
        "level": level,
        "source": source,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "read": False,
    }
    notifs.append(notif)
    if len(notifs) > 200:
        notifs = notifs[-200:]
    _save_json(_NOTIF_FILE, notifs)
    return f"NOTIFICATION_PUSHED|{notif['id']}|{title}: {message[:80]}"


def get_notifications(params: dict) -> str:
    """Get notifications, optionally filtered."""
    unread_only = str(params.get("unread_only", "false") or "false").lower() == "true"
    limit = int(params.get("limit", 20) or 20)

    notifs = _load_json(_NOTIF_FILE)
    if not isinstance(notifs, list):
        return "No notifications."

    if unread_only:
        notifs = [n for n in notifs if not n.get("read")]

    notifs = notifs[-limit:]
    if not notifs:
        return "No notifications."

    lines = []
    for n in notifs:
        read = "READ" if n.get("read") else "UNREAD"
        lines.append(f"  [{read}] [{n.get('level', 'info').upper()}] {n.get('title', '?')}: {n.get('message', '')[:60]} ({n.get('time', '?')})")
    return f"NOTIFICATIONS ({len(notifs)}):\n" + "\n".join(lines)


def mark_read(params: dict) -> str:
    """Mark notifications as read."""
    notif_id = str(params.get("notif_id", "") or "").strip()
    notifs = _load_json(_NOTIF_FILE)
    if not isinstance(notifs, list):
        return "No notifications."

    if notif_id:
        for n in notifs:
            if n.get("id") == notif_id:
                n["read"] = True
                _save_json(_NOTIF_FILE, notifs)
                return f"MARKED_READ|{notif_id}"
        return f"Notification {notif_id} not found."
    else:
        for n in notifs:
            n["read"] = True
        _save_json(_NOTIF_FILE, notifs)
        return "ALL_MARKED_READ"


def schedule_alert(params: dict) -> str:
    """Schedule a future alert."""
    message = str(params.get("message", "") or "").strip()
    delay_seconds = int(params.get("delay_seconds", 0) or 0)
    delay_minutes = int(params.get("delay_minutes", 0) or 0)
    repeat = str(params.get("repeat", "once") or "once").strip()

    if not message:
        return "ERROR: Provide a message for the alert."
    total_delay = delay_seconds + (delay_minutes * 60)
    if total_delay <= 0:
        return "ERROR: Provide delay_seconds or delay_minutes."

    alerts = _load_json(_SCHEDULE_FILE)
    if not isinstance(alerts, list):
        alerts = []

    alert = {
        "id": f"a_{int(time.time())}",
        "message": message,
        "fire_at": time.time() + total_delay,
        "repeat": repeat,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "fired": False,
    }
    alerts.append(alert)
    _save_json(_SCHEDULE_FILE, alerts)
    return f"ALERT_SCHEDULED|{alert['id']}|Fires in {total_delay}s: {message[:60]}"


def get_scheduled(params: dict) -> str:
    """List scheduled alerts."""
    alerts = _load_json(_SCHEDULE_FILE)
    if not isinstance(alerts, list) or not alerts:
        return "No scheduled alerts."

    lines = []
    now = time.time()
    for a in alerts:
        if a.get("fired") and a.get("repeat") == "once":
            continue
        remaining = max(0, int(a.get("fire_at", 0) - now))
        status = f"in {remaining}s" if remaining > 0 else "DUE"
        lines.append(f"  [{a.get('id', '?')}] {a.get('message', '')[:50]} ({status}, repeat: {a.get('repeat', 'once')})")
    return f"SCHEDULED ALERTS ({len(lines)}):\n" + "\n".join(lines)


def cancel_alert(params: dict) -> str:
    """Cancel a scheduled alert."""
    alert_id = str(params.get("alert_id", "") or "").strip()
    alerts = _load_json(_SCHEDULE_FILE)
    if not isinstance(alerts, list):
        return "No alerts to cancel."

    before = len(alerts)
    alerts = [a for a in alerts if a.get("id") != alert_id]
    if len(alerts) < before:
        _save_json(_SCHEDULE_FILE, alerts)
        return f"ALERT_CANCELLED|{alert_id}"
    return f"Alert {alert_id} not found."


def check_due_alerts() -> list[dict]:
    """Check for alerts that are due (called by autonomous monitor)."""
    alerts = _load_json(_SCHEDULE_FILE)
    if not isinstance(alerts, list):
        return []

    now = time.time()
    due = []
    for a in alerts:
        if a.get("fired") and a.get("repeat") == "once":
            continue
        if now >= a.get("fire_at", float("inf")):
            due.append(a)
            if a.get("repeat") == "once":
                a["fired"] = True
            else:
                intervals = {"hourly": 3600, "daily": 86400, "weekly": 604800}
                a["fire_at"] = now + intervals.get(a.get("repeat", "once"), 86400)

    _save_json(_SCHEDULE_FILE, alerts)
    return due


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "push") or "push").lower()

    if action == "push":
        return push_notification(params)
    elif action == "get":
        return get_notifications(params)
    elif action == "read":
        return mark_read(params)
    elif action == "schedule":
        return schedule_alert(params)
    elif action == "scheduled":
        return get_scheduled(params)
    elif action == "cancel":
        return cancel_alert(params)
    return f"Unknown action: {action}. Valid: push, get, read, schedule, scheduled, cancel"

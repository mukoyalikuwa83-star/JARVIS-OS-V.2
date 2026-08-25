"""Alarm and timer system — countdown timers, recurring alarms, stopwatch."""

import json
import time
import threading
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / ".jarvis"
_ALARMS_FILE = _MEMORY_DIR / "alarms.json"
_TIMERS_FILE = _MEMORY_DIR / "timers.json"


def _load_json(path: Path) -> list | dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [] if "alarm" in path.name else []


def _save_json(path: Path, data):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_active_timers: dict[str, threading.Timer] = {}


def set_alarm(params: dict) -> str:
    """Set an alarm at a specific time."""
    time_str = str(params.get("time", "") or "").strip()
    label = str(params.get("label", "") or "Alarm").strip()
    repeat = str(params.get("repeat", "once") or "once").strip().lower()

    if not time_str:
        return "ERROR: Provide alarm time (e.g. '7:30 AM', '14:00')."

    try:
        now = time.localtime()
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
            try:
                parsed = time.strptime(time_str, fmt)
                alarm_hour = parsed.tm_hour
                alarm_min = parsed.tm_min
                break
            except ValueError:
                continue
        else:
            return f"ERROR: Could not parse time '{time_str}'. Use formats like '7:30 AM' or '14:00'."

        import datetime
        now_dt = datetime.datetime.now()
        alarm_dt = now_dt.replace(hour=alarm_hour, minute=alarm_min, second=0, microsecond=0)
        if alarm_dt <= now_dt:
            alarm_dt += datetime.timedelta(days=1)
        delay = (alarm_dt - now_dt).total_seconds()

        alarms = _load_json(_ALARMS_FILE)
        if not isinstance(alarms, list):
            alarms = []

        alarm = {
            "id": f"alarm_{int(time.time())}",
            "time": time_str,
            "label": label,
            "repeat": repeat,
            "fire_at": time.time() + delay,
            "active": True,
            "created": time.strftime("%Y-%m-%d %H:%M"),
        }
        alarms.append(alarm)
        _save_json(_ALARMS_FILE, alarms)

        def _fire():
            try:
                _do_fire_alarm(alarm["id"], label)
            except Exception:
                pass

        timer = threading.Timer(delay, _fire)
        timer.daemon = True
        timer.start()
        _active_timers[alarm["id"]] = timer

        mins = int(delay // 60)
        return f"ALARM_SET|{alarm['id']}|{label} at {time_str} (in {mins}m). Repeat: {repeat}"
    except Exception as e:
        return f"ALARM_ERROR|{e}"


def _do_fire_alarm(alarm_id: str, label: str):
    """Fire an alarm — play sound and notify."""
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 500)
            time.sleep(0.3)
    except Exception:
        pass

    try:
        from actions.notification_center import push_notification
        push_notification({"title": f"ALARM: {label}", "message": "Time's up!", "level": "success", "source": "alarm"})
    except Exception:
        pass

    alarms = _load_json(_ALARMS_FILE)
    if isinstance(alarms, list):
        for a in alarms:
            if a.get("id") == alarm_id:
                if a.get("repeat") == "once":
                    a["active"] = False
                else:
                    intervals = {"hourly": 3600, "daily": 86400, "weekly": 604800}
                    a["fire_at"] = time.time() + intervals.get(a["repeat"], 86400)
                break
        _save_json(_ALARMS_FILE, alarms)


def set_timer(params: dict) -> str:
    """Set a countdown timer."""
    seconds = int(params.get("seconds", 0) or 0)
    minutes = int(params.get("minutes", 0) or 0)
    label = str(params.get("label", "") or "Timer").strip()

    total = seconds + (minutes * 60)
    if total <= 0:
        return "ERROR: Provide seconds or minutes."

    timer_id = f"timer_{int(time.time())}"

    def _fire():
        try:
            import winsound
            for _ in range(5):
                winsound.Beep(800, 300)
                time.sleep(0.2)
        except Exception:
            pass
        try:
            from actions.notification_center import push_notification
            push_notification({"title": f"TIMER DONE: {label}", "message": f"{total}s timer finished!", "level": "success", "source": "timer"})
        except Exception:
            pass
        _active_timers.pop(timer_id, None)

    timer = threading.Timer(total, _fire)
    timer.daemon = True
    timer.start()
    _active_timers[timer_id] = timer

    mins, secs = divmod(total, 60)
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    return f"TIMER_SET|{timer_id}|{label}: {time_str} countdown started."


def stop_timer(params: dict) -> str:
    """Stop a running timer."""
    timer_id = str(params.get("timer_id", "") or "").strip()
    if timer_id in _active_timers:
        _active_timers[timer_id].cancel()
        _active_timers.pop(timer_id)
        return f"TIMER_STOPPED|{timer_id}"
    return f"Timer {timer_id} not found or already stopped."


def list_alarms(params: dict) -> str:
    """List all alarms."""
    alarms = _load_json(_ALARMS_FILE)
    if not isinstance(alarms, list) or not alarms:
        return "No alarms set."

    active = [a for a in alarms if a.get("active")]
    if not active:
        return "No active alarms."

    lines = []
    for a in active:
        remaining = max(0, int(a.get("fire_at", 0) - time.time()))
        mins = remaining // 60
        lines.append(f"  [{a.get('id', '?')}] {a.get('label', '?')} at {a.get('time', '?')} (in {mins}m, {a.get('repeat', 'once')})")
    return f"ACTIVE ALARMS ({len(active)}):\n" + "\n".join(lines)


def list_timers(params: dict) -> str:
    """List active timers."""
    if not _active_timers:
        return "No active timers."
    lines = [f"  {tid}" for tid in _active_timers]
    return f"ACTIVE TIMERS ({len(_active_timers)}):\n" + "\n".join(lines)


def cancel_alarm(params: dict) -> str:
    """Cancel an alarm."""
    alarm_id = str(params.get("alarm_id", "") or "").strip()
    alarms = _load_json(_ALARMS_FILE)
    if not isinstance(alarms, list):
        return "No alarms."

    for a in alarms:
        if a.get("id") == alarm_id:
            a["active"] = False
            _save_json(_ALARMS_FILE, alarms)
            if alarm_id in _active_timers:
                _active_timers[alarm_id].cancel()
                _active_timers.pop(alarm_id)
            return f"ALARM_CANCELLED|{alarm_id}"
    return f"Alarm {alarm_id} not found."


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "set_alarm") or "set_alarm").lower()

    if action == "set_alarm":
        return set_alarm(params)
    elif action == "set_timer":
        return set_timer(params)
    elif action == "stop_timer":
        return stop_timer(params)
    elif action == "list_alarms":
        return list_alarms(params)
    elif action == "list_timers":
        return list_timers(params)
    elif action == "cancel_alarm":
        return cancel_alarm(params)
    return f"Unknown action: {action}. Valid: set_alarm, set_timer, stop_timer, list_alarms, list_timers, cancel_alarm"

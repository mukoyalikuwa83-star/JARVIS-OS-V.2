"""Proactive monitoring: check messages, battery, network, disk in background.
Runs periodically and alerts user when something needs attention."""

import subprocess
import os
import time
import json
import ctypes
from pathlib import Path


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _base_dir():
    return Path(__file__).resolve().parent.parent


def _state_file():
    return _base_dir() / ".jarvis" / "monitor_state.json"


def _load_state():
    try:
        return json.loads(_state_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state):
    try:
        _state_file().parent.mkdir(exist_ok=True)
        _state_file().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "check_all")

    handlers = {
        "check_all": _check_all,
        "check_battery": _check_battery,
        "check_disk": _check_disk,
        "check_network": _check_network,
        "check_cpu": _check_cpu,
        "check_messages": _check_messages,
        "check_calendar": _check_calendar,
        "check_reminders": _check_reminders,
        "get_alerts": _get_alerts,
        "clear_alerts": _clear_alerts,
        "get_status": _get_status,
        "set_threshold": lambda: _set_threshold(params.get("target", ""), params.get("value", "")),
    }

    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _check_all():
    alerts = []
    battery = _check_battery()
    if "WARNING" in battery or "CRITICAL" in battery:
        alerts.append(battery)
    disk = _check_disk()
    if "WARNING" in disk:
        alerts.append(disk)
    cpu = _check_cpu()
    if "WARNING" in cpu:
        alerts.append(cpu)
    if alerts:
        return "ALERTS:\n" + "\n".join(alerts)
    return "All systems nominal. No alerts."


def _check_battery():
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat is None:
            return "No battery detected (desktop)"
        percent = bat.percent
        plugged = bat.power_plugged
        secs = bat.secsleft
        if secs > 0:
            hours = secs // 3600
            mins = (secs % 3600) // 60
            time_left = f"{hours}h {mins}m"
        else:
            time_left = "calculating..."
        status = "CHARGING" if plugged else "ON BATTERY"
        if percent <= 10:
            return f"CRITICAL BATTERY: {percent}% ({status}) - {time_left} remaining. PLUG IN NOW!"
        elif percent <= 20 and not plugged:
            return f"WARNING BATTERY: {percent}% ({status}) - {time_left} remaining. Plug in soon."
        return f"Battery: {percent}% ({status}) - {time_left}"
    except Exception:
        out, _, _ = _run(["powershell", "-Command",
                          "(Get-WmiObject Win32_Battery).EstimatedChargeRemaining"], timeout=5)
        if out and out.isdigit():
            return f"Battery: {out}%"
        return "Battery status unavailable"


def _check_disk():
    state = _load_state()
    threshold = state.get("disk_threshold", 90)
    try:
        import psutil
        alerts = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                if usage.percent >= threshold:
                    free_gb = usage.free / (1024**3)
                    alerts.append(f"  {part.mountpoint}: {usage.percent}% used ({free_gb:.1f}GB free)")
            except Exception:
                continue
        if alerts:
            return f"WARNING DISK: {len(alerts)} drive(s) above {threshold}%:\n" + "\n".join(alerts)
        return "Disk: All drives healthy"
    except Exception:
        return "Disk check unavailable"


def _check_network():
    state = _load_state()
    threshold_mb = state.get("network_threshold", 100)
    try:
        import psutil
        net = psutil.net_io_counters()
        sent_mb = net.bytes_sent / (1024**2)
        recv_mb = net.bytes_recv / (1024**2)
        prev = state.get("prev_net", {})
        if prev:
            sent_diff = sent_mb - prev.get("sent", 0)
            recv_diff = recv_mb - prev.get("recv", 0)
            if recv_diff > threshold_mb:
                state["prev_net"] = {"sent": sent_mb, "recv": recv_mb}
                _save_state(state)
                return f"WARNING NETWORK: Downloaded {recv_diff:.1f}MB since last check"
        state["prev_net"] = {"sent": sent_mb, "recv": recv_mb}
        _save_state(state)
        return f"Network: Sent {sent_mb:.1f}MB, Received {recv_mb:.1f}MB total"
    except Exception:
        return "Network check unavailable"


def _check_cpu():
    state = _load_state()
    threshold = state.get("cpu_threshold", 90)
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        if cpu >= threshold:
            top = psutil.process_percent(5)
            return f"WARNING CPU: {cpu}% used. Top processes: {top}"
        return f"CPU: {cpu}%"
    except Exception:
        return "CPU check unavailable"


def _check_messages():
    return "Message monitoring: Use the send_message tool with action='read' to check WhatsApp/Instagram. Background monitoring requires the app to be open in browser."


def _check_calendar():
    try:
        from actions.calendar_control import handle as cal
        return cal({"action": "list"})
    except Exception as e:
        return f"Calendar check failed: {e}"


def _check_reminders():
    return "Reminders are managed by the system scheduler. Use 'reminder' tool with action='list' to see upcoming reminders."


def _get_alerts():
    state = _load_state()
    alerts = state.get("alerts", [])
    if not alerts:
        return "No alerts."
    return f"RECENT ALERTS ({len(alerts)}):\n" + "\n".join(alerts[-10:])


def _clear_alerts():
    state = _load_state()
    state["alerts"] = []
    _save_state(state)
    return "Alerts cleared."


def _get_status():
    battery = _check_battery()
    disk = _check_disk()
    cpu = _check_cpu()
    network = _check_network()
    return f"SYSTEM STATUS:\n{battery}\n{disk}\n{cpu}\n{network}"


def _set_threshold(name, value):
    state = _load_state()
    try:
        state[f"{name}_threshold"] = int(value)
        _save_state(state)
        return f"Set {name} threshold to {value}"
    except ValueError:
        return f"Invalid value: {value}"

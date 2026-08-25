"""Auto Start — auto-start on boot, always-on daemon, scheduled wake-ups."""

import subprocess
import os
import sys
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _ps(command, timeout=15):
    out, rc = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], timeout=timeout)
    return out if rc == 0 else ""


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    handlers = {
        "status": _auto_start_status,
        "enable": _enable_auto_start,
        "disable": _disable_auto_start,
        "add_startup": _add_to_startup,
        "remove_startup": _remove_from_startup,
        "add_task_scheduler": _add_task_scheduler,
        "remove_task_scheduler": _remove_task_scheduler,
        "wake_on_lan": _wake_on_lan,
        "schedule_wake": lambda: _schedule_wake(target),
        "is_running": _is_running,
        "start_daemon": _start_daemon,
        "stop_daemon": _stop_daemon,
        "daemon_status": _daemon_status,
    }
    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown auto_start action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _auto_start_status() -> str:
    lines = ["=== AUTO-START STATUS ==="]

    startup_check = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue).PSObject.Properties | Where-Object {$_.Name -like '*jarvis*'} | Select-Object Name,Value | ConvertTo-Json")
    if startup_check:
        lines.append(f"Startup registry: CONFIGURED")
    else:
        lines.append(f"Startup registry: NOT configured")

    task_check = _ps("Get-ScheduledTask -TaskName 'JARVIS*' -ErrorAction SilentlyContinue | Select-Object TaskName,State | ConvertTo-Json")
    if task_check:
        lines.append(f"Task Scheduler: CONFIGURED")
    else:
        lines.append(f"Task Scheduler: NOT configured")

    bat_path = Path(__file__).resolve().parent.parent / "JARVIS.bat"
    if bat_path.exists():
        lines.append(f"Launcher: {bat_path}")
    else:
        lines.append(f"Launcher: MISSING")

    lines.append(f"Python: {sys.executable}")
    lines.append(f"PID: {os.getpid()}")

    return "\n".join(lines)


def _enable_auto_start() -> str:
    results = []
    results.append(_add_to_startup())
    results.append(_add_task_scheduler())
    return "\n".join(results)


def _disable_auto_start() -> str:
    results = []
    results.append(_remove_from_startup())
    results.append(_remove_task_scheduler())
    return "\n".join(results)


def _add_to_startup() -> str:
    try:
        bat_path = Path(__file__).resolve().parent.parent / "JARVIS.bat"
        if not bat_path.exists():
            return f"JARVIS.bat not found at {bat_path}"

        _ps(f"""
        $regPath = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
        Set-ItemProperty -Path $regPath -Name 'JARVIS-OS' -Value '"{bat_path}"'
        """)

        check = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run').PSObject.Properties | Where-Object {$_.Name -eq 'JARVIS-OS'} | Select-Object -ExpandProperty Value")
        if check:
            return f"Added to Windows startup: {bat_path}"
        return "Startup registration may have failed — check manually"
    except Exception as e:
        return f"Startup error: {e}"


def _remove_from_startup() -> str:
    try:
        _ps("Remove-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'JARVIS-OS' -ErrorAction SilentlyContinue")
        return "Removed from Windows startup"
    except Exception as e:
        return f"Remove error: {e}"


def _add_task_scheduler() -> str:
    try:
        bat_path = Path(__file__).resolve().parent.parent / "JARVIS.bat"
        if not bat_path.exists():
            return f"JARVIS.bat not found"

        _ps(f"""
        $action = New-ScheduledTaskAction -Execute '"{bat_path}"' -WorkingDirectory '{bat_path.parent}'
        $trigger1 = New-ScheduledTaskTrigger -AtLogOn
        $trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
        Register-ScheduledTask -TaskName 'JARVIS-AutoStart' -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -Description 'JARVIS-OS autonomous assistant' -Force
        """)
        return "Added to Task Scheduler (runs at login + hourly check)"
    except Exception as e:
        return f"Task Scheduler error: {e}"


def _remove_task_scheduler() -> str:
    try:
        _ps("Unregister-ScheduledTask -TaskName 'JARVIS-AutoStart' -Confirm:$false -ErrorAction SilentlyContinue")
        return "Removed from Task Scheduler"
    except Exception as e:
        return f"Remove error: {e}"


def _wake_on_lan() -> str:
    return """Wake-on-LAN setup:
  1. Enable WoL in BIOS/UEFI
  2. Enable WoL in network adapter settings
  3. Use this command from another device:
     python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b'\\xff'*6 + b'\\x00'*6 + MAC_ADDRESS.replace(':','').decode('hex')*16, ('<broadcast>', 9))"

The AI can wake the PC remotely if WoL is configured."""


def _schedule_wake(time_str: str) -> str:
    if not time_str:
        time_str = "07:00"
    try:
        _ps(f"""
        $wakeTime = Get-Date -Hour {time_str.split(':')[0]} -Minute {time_str.split(':')[1]} -Second 0
        if ($wakeTime -lt (Get-Date)) {{ $wakeTime = $wakeTime.AddDays(1) }}
        $trigger = New-ScheduledTaskTrigger -Once -At $wakeTime
        $action = New-ScheduledTaskAction -Execute 'powershell' -Argument '-Command "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"'
        Register-ScheduledTask -TaskName 'JARVIS-Wake' -Action $action -Trigger $trigger -Force
        """)
        return f"Wake scheduled for {time_str}"
    except Exception as e:
        return f"Wake schedule error: {e}"


def _is_running() -> str:
    try:
        out = _ps("(Get-Process python* | Where-Object {$_.CommandLine -like '*main.py*'}).Count")
        count = int(out) if out and out.strip().isdigit() else 0
        if count > 0:
            return f"JARVIS is running ({count} process(es))"
        return "JARVIS is not running"
    except Exception:
        return "Cannot determine if JARVIS is running"


def _start_daemon() -> str:
    try:
        bat_path = Path(__file__).resolve().parent.parent / "JARVIS.bat"
        if not bat_path.exists():
            return f"JARVIS.bat not found at {bat_path}"

        _ps(f"Start-Process -FilePath '{bat_path}' -WindowStyle Minimized")
        return "JARVIS daemon started (minimized)"
    except Exception as e:
        return f"Start error: {e}"


def _stop_daemon() -> str:
    try:
        _ps("(Get-Process python* | Where-Object {$_.CommandLine -like '*main.py*'}) | Stop-Process -Force")
        return "JARVIS daemon stopped"
    except Exception as e:
        return f"Stop error: {e}"


def _daemon_status() -> str:
    try:
        out = _ps("Get-Process python* | Where-Object {$_.CommandLine -like '*main.py*'} | Select-Object Id,StartTime,CPU | ConvertTo-Json")
        if out:
            procs = json.loads(out) if out else []
            if isinstance(procs, dict):
                procs = [procs]
            parts = [f"  PID {p.get('Id','?')}: started {p.get('StartTime','?')}, CPU {p.get('CPU',0):.1f}s" for p in procs]
            return f"Daemon processes ({len(procs)}):\n" + "\n".join(parts)
        return "No daemon processes found"
    except Exception as e:
        return f"Status error: {e}"

"""Self-control: autonomous background monitoring, proactive system management, health checks, auto-fix, pattern learning, schedule management, and self-healing."""

import subprocess
import os
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

_STATE_FILE = _DATA_DIR / "self_control_state.json"
_SCHEDULE_FILE = _DATA_DIR / "auto_schedule.json"
_HEALTH_FILE = _DATA_DIR / "health_history.json"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _ps(command, timeout=15):
    out, rc = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], timeout=timeout)
    return out if rc == 0 else ""


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def handle(parameters: dict) -> str:
    action = parameters.get("action", "")
    target = parameters.get("target", "")
    value = parameters.get("value", "")
    handlers = {
        "health_check": _health_check,
        "full_diagnostic": _full_diagnostic,
        "auto_fix": _auto_fix,
        "get_status": _get_status,
        "get_uptime": _get_uptime,
        "get_running_summary": _get_running_summary,
        "optimize_system": _optimize_system,
        "clean_temp": _clean_temp,
        "clear_dns": _clear_dns,
        "flush_arp": _flush_arp,
        "repair_system": _repair_system,
        "check_disk_errors": _check_disk_errors,
        "defrag_analysis": _defrag_analysis,
        "power_profile": lambda: _power_profile(target),
        "scheduled_scan": _scheduled_scan,
        "threat_check": _threat_check,
        "privacy_check": _privacy_check,
        "network_health": _network_health,
        "startup_optimize": _startup_optimize,
        "memory_cleanup": _memory_cleanup,
        "process_audit": _process_audit,
        "auto_schedule_add": lambda: _auto_schedule_add(target, value),
        "auto_schedule_list": _auto_schedule_list,
        "auto_schedule_remove": lambda: _auto_schedule_remove(target),
        "auto_schedule_run": _auto_schedule_run,
        "learn_pattern": lambda: _learn_pattern(target, value),
        "get_patterns": _get_patterns,
        "system_report": _system_report,
        "performance_baseline": _performance_baseline,
        "compare_baseline": _compare_baseline,
        "get_alerts": _get_alerts,
        "clear_alerts": _clear_alerts,
        "self_heal": _self_heal,
        "auto_update_check": _auto_update_check,
    }
    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown self_control action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _health_check() -> str:
    checks = []

    def _safe_float(val, default=0.0):
        if not val:
            return default
        try:
            clean = val.strip().encode("ascii", "ignore").decode("ascii").strip()
            return float(clean) if clean else default
        except (ValueError, UnicodeDecodeError):
            return default

    cpu_out = _ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    cpu_pct = _safe_float(cpu_out)
    checks.append(f"CPU: {cpu_pct}%")

    ram_out = _ps("$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalPhysicalMemory - $os.FreePhysicalMemory) / $os.TotalPhysicalMemory * 100, 1)")
    ram_pct = _safe_float(ram_out)
    checks.append(f"RAM: {ram_pct}%")

    disk_out = _ps("(Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | ForEach-Object { [math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 1) }) -join ','")
    disks = [_safe_float(d) for d in disk_out.split(",") if d.strip()] if disk_out else []
    disk_str = ", ".join(f"{d}%" for d in disks if d > 0)
    checks.append(f"Disk(s): {disk_str or 'N/A'}")

    net_out = _ps("Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet 2>$null")
    checks.append(f"Internet: {'OK' if 'True' in str(net_out) else 'DOWN'}")

    temp_out = _ps("(Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace root/WMI -ErrorAction SilentlyContinue | Measure-Object -Property CurrentTemperature -Maximum).Maximum")
    if temp_out:
        try:
            temp_c = (_safe_float(temp_out) - 2732) / 10
            checks.append(f"CPU Temp: {temp_c:.0f}C {'WARNING' if temp_c > 80 else 'OK'}")
        except Exception:
            pass

    report = " | ".join(checks)
    state = _load_json(_STATE_FILE, {})
    state["last_health_check"] = _now_str()
    state["last_cpu"] = cpu_pct
    state["last_ram"] = ram_pct
    _save_json(_STATE_FILE, state)

    alerts = []
    if cpu_pct > 90:
        alerts.append("HIGH CPU")
    if ram_pct > 90:
        alerts.append("HIGH RAM")
    for i, d in enumerate(disks):
        if d > 90:
            alerts.append(f"DISK {i}: {d}% FULL")

    if alerts:
        report += f"\nALERTS: {', '.join(alerts)}"

    return report


def _full_diagnostic() -> str:
    sections = []
    sections.append("=== HEALTH ===")
    sections.append(_health_check())
    sections.append("\n=== NETWORK ===")
    sections.append(_network_health())
    sections.append("\n=== PROCESSES (Top CPU) ===")
    sections.append(_process_audit())
    sections.append("\n=== STARTUP ===")
    sections.append(_startup_optimize())
    sections.append("\n=== THREATS ===")
    sections.append(_threat_check())
    sections.append("\n=== PRIVACY ===")
    sections.append(_privacy_check())
    return "\n".join(sections)


def _auto_fix() -> str:
    fixes = []
    cpu_out = _ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    cpu_pct = float(cpu_out) if cpu_out else 0
    if cpu_pct > 85:
        heavy = _ps("Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name,CPU,WorkingSet64 | ConvertTo-Json")
        try:
            procs = json.loads(heavy) if heavy else []
            if isinstance(procs, dict):
                procs = [procs]
            for p in procs:
                name = p.get("Name", "")
                if name and name not in ("System", "Idle", "svchost", "csrss", "wininit", "lsass"):
                    _ps(f"Stop-Process -Name '{name}' -Force -ErrorAction SilentlyContinue")
                    fixes.append(f"Killed high-CPU process: {name}")
        except Exception:
            pass

    ram_out = _ps("$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalPhysicalMemory - $os.FreePhysicalMemory) / $os.TotalPhysicalMemory * 100, 1)")
    ram_pct = float(ram_out) if ram_out else 0
    if ram_pct > 85:
        _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
        _ps("Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue")
        fixes.append("Cleaned temp files and recycle bin")

    disk_out = _ps("Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object { $_.DeviceID + ':' + [math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100, 1) }")
    for line in (disk_out or "").split("\n"):
        if ":" in line:
            try:
                parts = line.strip().split(":")
                pct = float(parts[-1])
                if pct > 90:
                    fixes.append(f"DISK {parts[0]} at {pct}% — run deep cleanup")
            except Exception:
                pass

    _ps("ipconfig /flushdns | Out-Null")
    fixes.append("DNS cache flushed")

    _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    fixes.append("Recycle bin emptied")

    _save_json(_STATE_FILE, {
        "last_auto_fix": _now_str(),
        "fixes_applied": len(fixes),
    })

    return f"Auto-fix applied {len(fixes)} fixes:\n" + "\n".join(f"  - {f}" for f in fixes) if fixes else "System healthy — no fixes needed"


def _get_status() -> str:
    state = _load_json(_STATE_FILE, {})
    alerts = state.get("alerts", [])
    parts = [
        f"Last health check: {state.get('last_health_check', 'Never')}",
        f"Last auto-fix: {state.get('last_auto_fix', 'Never')}",
        f"Last optimization: {state.get('last_optimize', 'Never')}",
        f"Patterns learned: {len(state.get('patterns', {}))}",
        f"Active alerts: {len(alerts)}",
    ]
    if alerts:
        parts.append("Alerts:")
        for a in alerts[-5:]:
            parts.append(f"  - {a}")
    return "\n".join(parts)


def _get_uptime() -> str:
    try:
        out = _ps("(Get-CimInstance Win32_OperatingSystem).LastBootUpTime")
        if out:
            boot = datetime.strptime(out.strip()[:19], "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - boot
            days = delta.days
            hours = delta.seconds // 3600
            mins = (delta.seconds % 3600) // 60
            return f"Uptime: {days}d {hours}h {mins}m (since {out.strip()[:19]})"
    except Exception:
        pass
    return "Uptime unknown"


def _get_running_summary() -> str:
    try:
        out = _ps("""
        $procs = Get-Process | Where-Object {$_.CPU -gt 0} | Sort-Object CPU -Descending | Select-Object -First 10 Name,@{N='CPU_s';E={[math]::Round($_.CPU,1)}},@{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,0)}},Id
        $procs | ConvertTo-Json
        """)
        procs = json.loads(out) if out else []
        if isinstance(procs, dict):
            procs = [procs]
        parts = [f"[{p.get('Id','?')}] {p.get('Name','?')}: CPU {p.get('CPU_s',0)}s | RAM {p.get('RAM_MB',0)}MB" for p in procs]
        total = _ps("(Get-Process | Measure-Object -Property WorkingSet64 -Sum).Sum")
        total_mb = round(int(total) / 1024 / 1024) if total else "?"
        return f"Total RAM by processes: {total_mb}MB\nTop 10:\n" + "\n".join(parts) if parts else "No running processes"
    except Exception as e:
        return f"Process summary error: {e}"


def _optimize_system() -> str:
    steps = []
    _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    steps.append("Recycle bin emptied")

    _ps("Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue")
    steps.append("Temp files cleaned")

    _ps("ipconfig /flushdns | Out-Null")
    steps.append("DNS cache flushed")

    _ps("Remove-Item (Get-ChildItem $env:LOCALAPPDATA\\Microsoft\\Windows\\INetCache -Recurse -ErrorAction SilentlyContinue) -Recurse -Force -ErrorAction SilentlyContinue")
    steps.append("Internet cache cleared")

    _ps("powershell -Command 'Clear-Host' -ErrorAction SilentlyContinue")

    state = _load_json(_STATE_FILE, {})
    state["last_optimize"] = _now_str()
    _save_json(_STATE_FILE, state)

    return f"System optimized ({len(steps)} steps):\n" + "\n".join(f"  - {s}" for s in steps)


def _clean_temp() -> str:
    try:
        before = _ps("(Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum")
        before_mb = round(int(before) / 1024 / 1024) if before else 0
        _ps("Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue")
        after = _ps("(Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum")
        after_mb = round(int(after) / 1024 / 1024) if after else 0
        freed = before_mb - after_mb
        return f"Temp cleaned: freed ~{freed}MB ({before_mb}MB -> {after_mb}MB)"
    except Exception as e:
        return f"Temp clean error: {e}"


def _clear_dns() -> str:
    try:
        out = _ps("ipconfig /flushdns")
        return f"DNS cache flushed: {out}" if out else "DNS cache flushed"
    except Exception as e:
        return f"DNS flush error: {e}"


def _flush_arp() -> str:
    try:
        out = _ps("netsh interface ip delete arpcache")
        return "ARP cache flushed"
    except Exception as e:
        return f"ARP flush error: {e}"


def _repair_system() -> str:
    try:
        out, rc = _run(["sfc", "/scannow"], timeout=300)
        return f"System scan complete:\n{out[-500:]}" if out else "System scan initiated (may take a while)"
    except Exception as e:
        return f"System repair error: {e}"


def _check_disk_errors() -> str:
    try:
        out = _ps("chkdsk C: /F /R 2>&1 | Select-Object -Last 10")
        return f"Disk check:\n{out}" if out else "Disk check initiated"
    except Exception as e:
        return f"Disk check error: {e}"


def _defrag_analysis() -> str:
    try:
        out = _ps("defrag C: /A /V | Select-Object -Last 15", timeout=120)
        return f"Defrag analysis:\n{out}" if out else "Defrag analysis unavailable"
    except Exception as e:
        return f"Defrag error: {e}"


def _power_profile(profile: str = "high") -> str:
    if not profile:
        profile = "high"
    try:
        profiles = {"high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                     "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
                     "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4b"}
        guid = profiles.get(profile.lower(), profiles["high"])
        _ps(f"powercfg /setactive {guid}")
        return f"Power profile set to: {profile}"
    except Exception as e:
        return f"Power profile error: {e}"


def _scheduled_scan() -> str:
    try:
        _ps("Start-MpScan -ScanType QuickScan")
        return "Windows Defender quick scan started"
    except Exception as e:
        return f"Scan error: {e}"


def _threat_check() -> str:
    try:
        out = _ps("Get-MpThreatDetection | Select-Object -First 5 ThreatID,DomainUser,ProcessName,DetectionTime | ConvertTo-Json")
        threats = json.loads(out) if out else []
        if isinstance(threats, dict):
            threats = [threats]
        if threats:
            parts = [f"Threat {t.get('ThreatID','?')}: {t.get('ProcessName','?')} at {t.get('DetectionTime','?')}" for t in threats]
            return "THREATS DETECTED:\n" + "\n".join(parts)
        return "No threats detected"
    except Exception as e:
        return f"Threat check error: {e}"


def _privacy_check() -> str:
    checks = []
    cam_access = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam' -ErrorAction SilentlyContinue).Value")
    checks.append(f"Camera access: {cam_access or 'Unknown'}")

    mic_access = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone' -ErrorAction SilentlyContinue).Value")
    checks.append(f"Microphone access: {mic_access or 'Unknown'}")

    loc_access = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location' -ErrorAction SilentlyContinue).Value")
    checks.append(f"Location access: {loc_access or 'Unknown'}")

    diag_data = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Diagnostics\\DiagTrack' -ErrorAction SilentlyContinue).ShowedToastAtLevel")
    checks.append(f"Diagnostics level: {diag_data or 'Unknown'}")

    return "\n".join(checks)


def _network_health() -> str:
    checks = []
    ping = _ps("Test-Connection -ComputerName 8.8.8.8 -Count 2 -Quiet 2>$null")
    checks.append(f"Internet: {'UP' if 'True' in ping else 'DOWN'}")

    dns = _ps("(Resolve-DnsName google.com -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1")
    checks.append(f"DNS: {'OK' if dns else 'FAILED'}")

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("google.com", 443))
        s.close()
        checks.append("HTTPS: OK")
    except Exception:
        checks.append("HTTPS: FAILED")

    adapter = _ps("Get-NetAdapter -Physical | Where-Object {$_.Status -eq 'Up'} | Select-Object Name,LinkSpeed | ConvertTo-Json")
    try:
        ad = json.loads(adapter) if adapter else {}
        if isinstance(ad, list):
            ad = ad[0] if ad else {}
        checks.append(f"Adapter: {ad.get('Name','?')} @ {ad.get('LinkSpeed','?')}")
    except Exception:
        pass

    gateway = _ps("(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1).NextHop")
    checks.append(f"Gateway: {gateway or 'Unknown'}")

    return " | ".join(checks)


def _startup_optimize() -> str:
    try:
        out = _ps("Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Sort-Object Name | ConvertTo-Json")
        apps = json.loads(out) if out else []
        if isinstance(apps, dict):
            apps = [apps]
        parts = []
        for a in apps:
            cmd = a.get("Command", "")
            if len(cmd) > 60:
                cmd = cmd[:60] + "..."
            parts.append(f"  {a.get('Name','?')}: {cmd}")
        return f"Startup apps ({len(apps)}):\n" + "\n".join(parts) if parts else "No startup apps"
    except Exception as e:
        return f"Startup error: {e}"


def _memory_cleanup() -> str:
    try:
        _ps("[System.GC]::Collect()")
        _ps("[System.GC]::WaitForPendingFinalizers()")
        return "Garbage collection forced"
    except Exception as e:
        return f"Memory cleanup error: {e}"


def _process_audit() -> str:
    try:
        out = _ps("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name,@{N='CPU_s';E={[math]::Round($_.CPU,1)}},@{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,0)}},Id | ConvertTo-Json")
        procs = json.loads(out) if out else []
        if isinstance(procs, dict):
            procs = [procs]
        parts = [f"[{p.get('Id','?')}] {p.get('Name','?')}: CPU {p.get('CPU_s',0)}s | {p.get('RAM_MB',0)}MB" for p in procs]
        return "Top CPU processes:\n" + "\n".join(parts) if parts else "No processes"
    except Exception as e:
        return f"Process audit error: {e}"


def _auto_schedule_add(task_type: str, schedule: str) -> str:
    if not task_type or not schedule:
        return "Provide task_type (health_check, scan, optimize) and schedule (daily, hourly, boot)"
    schedules = _load_json(_SCHEDULE_FILE, {"tasks": []})
    task = {
        "id": str(int(time.time())),
        "type": task_type,
        "schedule": schedule,
        "created": _now_str(),
        "enabled": True,
    }
    schedules["tasks"].append(task)
    _save_json(_SCHEDULE_FILE, schedules)
    return f"Schedule added: {task_type} every {schedule} (ID: {task['id']})"


def _auto_schedule_list() -> str:
    schedules = _load_json(_SCHEDULE_FILE, {"tasks": []})
    tasks = schedules.get("tasks", [])
    if not tasks:
        return "No scheduled tasks"
    parts = [f"[{t.get('id','?')}] {t.get('type','?')} every {t.get('schedule','?')} {'ON' if t.get('enabled') else 'OFF'}" for t in tasks]
    return "\n".join(parts)


def _auto_schedule_remove(task_id: str) -> str:
    if not task_id:
        return "Provide task ID"
    schedules = _load_json(_SCHEDULE_FILE, {"tasks": []})
    before = len(schedules["tasks"])
    schedules["tasks"] = [t for t in schedules["tasks"] if t.get("id") != task_id]
    _save_json(_SCHEDULE_FILE, schedules)
    after = len(schedules["tasks"])
    return f"Removed {before - after} task(s)" if before > after else "Task not found"


def _auto_schedule_run() -> str:
    schedules = _load_json(_SCHEDULE_FILE, {"tasks": []})
    results = []
    for task in schedules.get("tasks", []):
        if not task.get("enabled"):
            continue
        task_type = task.get("type", "")
        if task_type == "health_check":
            results.append(f"health_check: {_health_check()[:200]}")
        elif task_type == "scan":
            results.append("scan: Quick scan triggered")
            _ps("Start-MpScan -ScanType QuickScan")
        elif task_type == "optimize":
            results.append(f"optimize: {_optimize_system()[:200]}")
    return f"Ran {len(results)} scheduled task(s):\n" + "\n".join(results) if results else "No tasks to run"


def _learn_pattern(category: str, observation: str) -> str:
    if not category or not observation:
        return "Provide category and observation"
    state = _load_json(_STATE_FILE, {})
    patterns = state.get("patterns", {})
    if category not in patterns:
        patterns[category] = []
    patterns[category].append({
        "observation": observation,
        "time": _now_str(),
    })
    patterns[category] = patterns[category][-50:]
    state["patterns"] = patterns
    _save_json(_STATE_FILE, state)
    return f"Pattern learned ({category}): {observation[:80]}"


def _get_patterns() -> str:
    state = _load_json(_STATE_FILE, {})
    patterns = state.get("patterns", {})
    if not patterns:
        return "No patterns learned yet"
    parts = []
    for cat, obs in patterns.items():
        recent = obs[-3:] if obs else []
        obs_str = "; ".join(o.get("observation", "")[:40] for o in recent)
        parts.append(f"  {cat} ({len(obs)} observations): {obs_str}")
    return "Learned patterns:\n" + "\n".join(parts)


def _system_report() -> str:
    sections = []
    sections.append(_health_check())
    sections.append(f"\n{_get_uptime()}")
    sections.append(f"\n{_network_health()}")
    sections.append(f"\n{_get_running_summary()[:300]}")
    sections.append(f"\n{_privacy_check()}")
    state = _load_json(_STATE_FILE, {})
    sections.append(f"\nPatterns: {len(state.get('patterns', {}))} categories")
    sections.append(f"Last optimize: {state.get('last_optimize', 'Never')}")
    return "\n".join(sections)


def _performance_baseline() -> str:
    metrics = {}
    cpu_out = _ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    metrics["cpu"] = float(cpu_out) if cpu_out else 0
    ram_out = _ps("$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalPhysicalMemory - $os.FreePhysicalMemory) / $os.TotalPhysicalMemory * 100, 1)")
    metrics["ram"] = float(ram_out) if ram_out else 0
    metrics["timestamp"] = _now_str()
    state = _load_json(_STATE_FILE, {})
    state["baseline"] = metrics
    _save_json(_STATE_FILE, state)
    return f"Baseline recorded: CPU {metrics['cpu']}% | RAM {metrics['ram']}% at {metrics['timestamp']}"


def _compare_baseline() -> str:
    state = _load_json(_STATE_FILE, {})
    baseline = state.get("baseline", {})
    if not baseline:
        return "No baseline recorded. Run performance_baseline first."
    cpu_out = _ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    current_cpu = float(cpu_out) if cpu_out else 0
    ram_out = _ps("$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalPhysicalMemory - $os.FreePhysicalMemory) / $os.TotalPhysicalMemory * 100, 1)")
    current_ram = float(ram_out) if ram_out else 0
    cpu_diff = current_cpu - baseline.get("cpu", 0)
    ram_diff = current_ram - baseline.get("ram", 0)
    parts = [
        f"Baseline ({baseline.get('timestamp', '?')}): CPU {baseline.get('cpu',0)}% | RAM {baseline.get('ram',0)}%",
        f"Current: CPU {current_cpu}% | RAM {current_ram}%",
        f"CPU change: {'+' if cpu_diff >= 0 else ''}{cpu_diff:.1f}%",
        f"RAM change: {'+' if ram_diff >= 0 else ''}{ram_diff:.1f}%",
    ]
    if cpu_diff > 20:
        parts.append("WARNING: Significant CPU increase since baseline")
    if ram_diff > 20:
        parts.append("WARNING: Significant RAM increase since baseline")
    return "\n".join(parts)


def _get_alerts() -> str:
    state = _load_json(_STATE_FILE, {})
    alerts = state.get("alerts", [])
    if not alerts:
        return "No active alerts"
    parts = [f"  [{a.get('time','?')}] {a.get('message','?')}" for a in alerts[-10:]]
    return f"Active alerts ({len(alerts)}):\n" + "\n".join(parts)


def _clear_alerts() -> str:
    state = _load_json(_STATE_FILE, {})
    count = len(state.get("alerts", []))
    state["alerts"] = []
    _save_json(_STATE_FILE, state)
    return f"Cleared {count} alerts"


def _self_heal() -> str:
    steps = []
    out = _ps("Get-Service -Name wuauserv -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if out and "Running" not in out:
        _ps("Start-Service -Name wuauserv -ErrorAction SilentlyContinue")
        steps.append("Restarted Windows Update service")

    out = _ps("Get-Service -Name BITS -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if out and "Running" not in out:
        _ps("Start-Service -Name BITS -ErrorAction SilentlyContinue")
        steps.append("Restarted BITS service")

    out = _ps("Get-Service -Name WinDefend -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if out and "Running" not in out:
        _ps("Start-Service -Name WinDefend -ErrorAction SilentlyContinue")
        steps.append("Restarted Windows Defender service")

    _ps("ipconfig /flushdns | Out-Null")
    steps.append("DNS cache flushed")

    _ps("[System.GC]::Collect()")
    steps.append("Garbage collection forced")

    return f"Self-heal completed ({len(steps)} steps):\n" + "\n".join(f"  - {s}" for s in steps) if steps else "System healthy — no healing needed"


def _auto_update_check() -> str:
    try:
        out = _ps("Get-WindowsUpdate -ErrorAction SilentlyContinue | Select-Object -First 5 Title,Size,Severity | ConvertTo-Json")
        updates = json.loads(out) if out else []
        if isinstance(updates, dict):
            updates = [updates]
        if updates:
            parts = [f"  {u.get('Title','?')} ({u.get('Size','?')}) [{u.get('Severity','?')}]" for u in updates]
            return f"Available updates ({len(updates)}):\n" + "\n".join(parts)
        return "No updates available"
    except Exception:
        try:
            out = _ps("Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 3 HotFixID,Description,InstalledOn | ConvertTo-Json")
            updates = json.loads(out) if out else []
            if isinstance(updates, dict):
                updates = [updates]
            parts = [f"{u.get('HotFixID','?')}: {u.get('Description','?')} ({u.get('InstalledOn','?')})" for u in updates]
            return "Recent updates:\n" + "\n".join(parts) if parts else "Update check unavailable"
        except Exception as e:
            return f"Update check error: {e}"

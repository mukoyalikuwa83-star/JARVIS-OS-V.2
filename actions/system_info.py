"""System information: time, date, battery, CPU, RAM, disk, network, IP, WiFi details."""

import datetime
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

_OS = sys.platform


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def get_time(params=None):
    now = datetime.datetime.now()
    return json.dumps({
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "timezone": str(datetime.datetime.now().astimezone().tzinfo),
        "unix_timestamp": int(now.timestamp()),
    })


def get_battery(params=None):
    if _OS == "win32":
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat:
                return json.dumps({
                    "percent": bat.percent,
                    "plugged": bat.power_plugged,
                    "time_left_seconds": bat.secsleft if bat.secsleft > 0 else None,
                    "status": "charging" if bat.power_plugged else "discharging",
                })
        except ImportError:
            out = _run(["powershell", "-Command",
                        "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,ChargingState | ConvertTo-Json"])
            if out:
                try:
                    d = json.loads(out)
                    return json.dumps({"percent": d.get("EstimatedChargeRemaining", -1),
                                       "status": "charging" if d.get("ChargingState") == 2 else "discharging"})
                except Exception:
                    pass
        return json.dumps({"percent": -1, "status": "no battery or desktop"})
    elif _OS == "darwin":
        out = _run(["pm", "-g", "-b", "accperc"])
        if out:
            lines = out.strip().split("\n")
            for line in lines:
                if "%" in line:
                    pct = line.split("%")[0].strip().split()[-1]
                    return json.dumps({"percent": int(pct), "status": "unknown"})
        return json.dumps({"percent": -1, "status": "no battery"})
    else:
        out = _run(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"])
        if out:
            for line in out.split("\n"):
                if "percentage" in line:
                    pct = line.split(":")[-1].strip().replace("%", "")
                    return json.dumps({"percent": int(pct), "status": "unknown"})
        return json.dumps({"percent": -1, "status": "no battery"})


def get_cpu_info(params=None):
    info = {"platform": platform.system(), "processor": platform.processor(), "cores": os.cpu_count()}
    if _OS == "win32":
        try:
            import psutil
            info["usage_percent"] = psutil.cpu_percent(interval=1)
            info["freq_mhz"] = psutil.cpu_freq().current if psutil.cpu_freq() else None
            info["per_core"] = psutil.cpu_percent(interval=0.5, percpu=True)
        except ImportError:
            out = _run(["powershell", "-Command",
                        "Get-CimInstance Win32_Processor | Select-Object LoadPercentage,Name | ConvertTo-Json"])
            if out:
                try:
                    d = json.loads(out)
                    if isinstance(d, list):
                        d = d[0]
                    info["usage_percent"] = d.get("LoadPercentage")
                    info["name"] = d.get("Name", "")
                except Exception:
                    pass
    elif _OS == "linux":
        load = _run(["cat", "/proc/loadavg"])
        if load:
            info["load_avg"] = load.split()[:3]
    return json.dumps(info)


def get_ram_info(params=None):
    info = {}
    if _OS == "win32":
        try:
            import psutil
            vm = psutil.virtual_memory()
            info = {
                "total_gb": round(vm.total / (1024**3), 1),
                "used_gb": round(vm.used / (1024**3), 1),
                "available_gb": round(vm.available / (1024**3), 1),
                "percent_used": vm.percent,
            }
        except ImportError:
            out = _run(["powershell", "-Command",
                        "$os=Get-CimInstance Win32_OperatingSystem; "
                        "@{Total=[math]::Round($os.TotalVisibleMemorySize/1MB,1);"
                        "Free=[math]::Round($os.FreePhysicalMemory/1MB,1)} | ConvertTo-Json"])
            if out:
                try:
                    d = json.loads(out)
                    total = d.get("Total", 0)
                    free = d.get("Free", 0)
                    info = {"total_gb": total, "available_gb": free, "used_gb": round(total - free, 1),
                            "percent_used": round((total - free) / total * 100, 1) if total else 0}
                except Exception:
                    pass
    elif _OS == "linux":
        out = _run(["free", "-b"])
        if out:
            parts = out.split("\n")[1].split()
            total = int(parts[1])
            available = int(parts[6]) if len(parts) > 6 else int(parts[3])
            info = {"total_gb": round(total / (1024**3), 1), "available_gb": round(available / (1024**3), 1),
                    "used_gb": round((total - available) / (1024**3), 1)}
    return json.dumps(info)


def get_disk_info(params=None):
    disks = []
    if _OS == "win32":
        try:
            import psutil
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mount": part.mountpoint,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent_used": usage.percent,
                    })
                except PermissionError:
                    continue
        except ImportError:
            out = _run(["powershell", "-Command",
                        "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json"])
            if out:
                try:
                    data = json.loads(out)
                    if isinstance(data, dict):
                        data = [data]
                    for d in data:
                        total = d.get("Size", 0)
                        free = d.get("FreeSpace", 0)
                        disks.append({"device": d.get("DeviceID", "?"),
                                      "total_gb": round(total / (1024**3), 1),
                                      "free_gb": round(free / (1024**3), 1),
                                      "used_gb": round((total - free) / (1024**3), 1)})
                except Exception:
                    pass
    elif _OS == "linux":
        out = _run(["df", "-BG", "--output=source,size,used,avail,target"])
        if out:
            for line in out.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 5 and parts[0].startswith("/"):
                    disks.append({"device": parts[0], "total_gb": int(parts[1].replace("G", "")),
                                  "used_gb": int(parts[2].replace("G", "")),
                                  "free_gb": int(parts[3].replace("G", "")), "mount": parts[4]})
    return json.dumps(disks)


def get_network_info(params=None):
    info = {}
    if _OS == "win32":
        out = _run(["powershell", "-Command",
                     "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne '127.0.0.1'} | "
                     "Select-Object IPAddress,InterfaceAlias,PrefixLength | ConvertTo-Json"])
        if out:
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                info["ipv4_addresses"] = [{"ip": d.get("IPAddress"), "interface": d.get("InterfaceAlias"),
                                           "prefix": d.get("PrefixLength")} for d in data]
            except Exception:
                pass
        out2 = _run(["powershell", "-Command",
                     "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                     "Select-Object Name,LinkSpeed,MacAddress | ConvertTo-Json"])
        if out2:
            try:
                data2 = json.loads(out2)
                if isinstance(data2, dict):
                    data2 = [data2]
                info["active_adapters"] = [{"name": d.get("Name"), "speed": d.get("LinkSpeed"),
                                            "mac": d.get("MacAddress")} for d in data2]
            except Exception:
                pass
    elif _OS == "linux":
        out = _run(["ip", "-4", "addr", "show"])
        if out:
            info["raw"] = out[:500]
    out3 = _run(["ping", "-n", "1", "8.8.8.8"], timeout=5) if _OS == "win32" else _run(["ping", "-c", "1", "8.8.8.8"], timeout=5)
    info["internet_reachable"] = "TTL=" in out3 or "ttl=" in out3 or "time=" in out3
    return json.dumps(info)


def get_wifi_info(params=None):
    info = {}
    if _OS == "win32":
        out = _run(["netsh", "wlan", "show", "interfaces"])
        if out:
            for line in out.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower().replace(" ", "_")
                    v = v.strip()
                    if k in ("ssid", "state", "signal", "radio_type", "authentication", "channel", "bssid"):
                        info[k] = v
        profile_out = _run(["netsh", "wlan", "show", "profiles"])
        if profile_out:
            profiles = []
            for line in profile_out.split("\n"):
                if "All User Profile" in line or "All Users Profile" in line:
                    name = line.split(":", 1)[-1].strip() if ":" in line else ""
                    if name:
                        profiles.append(name)
            info["saved_profiles"] = profiles
    elif _OS == "darwin":
        out = _run(["networksetup", "-getairportnetwork", "en0"])
        info["connected_network"] = out.replace("Current Wi-Fi Network: ", "") if out else "not connected"
    elif _OS == "linux":
        out = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
        if out:
            networks = []
            for line in out.split("\n"):
                parts = line.split(":")
                if len(parts) >= 3:
                    networks.append({"ssid": parts[0], "signal": parts[1] + "%", "security": parts[2]})
            info["available_networks"] = networks[:20]
        conn = _run(["nmcli", "-t", "-f", "SSID", "dev", "wifi", "show-password"])
        info["connected_network"] = conn.split("\n")[0] if conn else "unknown"
    return json.dumps(info)


def system_info(params=None):
    action = str(params.get("action", "all")).lower() if params else "all"
    dispatch = {
        "time": get_time,
        "battery": get_battery,
        "cpu": get_cpu_info,
        "ram": get_ram_info,
        "disk": get_disk_info,
        "network": get_network_info,
        "wifi": get_wifi_info,
    }
    if action == "all":
        results = {}
        for name, fn in dispatch.items():
            try:
                results[name] = json.loads(fn())
            except Exception:
                results[name] = fn()
        results["os"] = platform.system()
        results["hostname"] = platform.node()
        results["python_version"] = platform.python_version()
        return json.dumps(results)
    fn = dispatch.get(action)
    if fn:
        return fn(params)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(dispatch)}"})


def handle(parameters=None, player=None, **_kwargs):
    return system_info(parameters)

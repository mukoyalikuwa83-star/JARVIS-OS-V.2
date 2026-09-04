"""
Cybersecurity Monitoring Module for JARVIS.
Network scanning, port monitoring, intrusion detection, malware scanning.
Requires: requests (installed), optional nmap, scapy packages
"""
import os
import time
import json
import socket
import subprocess
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_SECURITY_LOG = _DATA_DIR / "security_log.json"

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "scan_ports":
        return _scan_ports(params)
    elif action == "scan_network":
        return _scan_network(params)
    elif action == "check_firewall":
        return _check_firewall()
    elif action == "check_updates":
        return _check_windows_updates()
    elif action == "malware_scan":
        return _malware_scan(params)
    elif action == "check_passwords":
        return _check_weak_passwords()
    elif action == "check_connections":
        return _check_active_connections()
    elif action == "security_report":
        return _security_report()
    elif action == "log":
        return _log_event(params)
    elif action == "check_ssl":
        return _check_ssl(params)
    elif action == "status":
        return _security_status()
    else:
        return "Security: scan_ports|scan_network|check_firewall|check_updates|malware_scan|check_passwords|check_connections|security_report|log|check_ssl|status"

def _scan_ports(params):
    host = params.get("host", "127.0.0.1")
    ports = params.get("ports", "21,22,23,25,53,80,110,143,443,993,995,3306,3389,5432,8080,8443")
    port_list = [int(p.strip()) for p in str(ports).split(",") if p.strip().isdigit()]
    open_ports = []
    for port in port_list:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            result = s.connect_ex((host, port))
            if result == 0:
                open_ports.append(port)
            s.close()
        except Exception:
            pass
    if open_ports:
        return f"Open ports on {host}: {open_ports}"
    return f"No open ports found on {host} (scanned {len(port_list)} ports)"

def _scan_network(params):
    try:
        import requests
        subnet = params.get("subnet", _get_local_subnet())
        if not subnet:
            return "Could not determine local subnet"
        alive = []
        for i in range(1, 20):
            ip = f"{subnet}.{i}"
            try:
                r = requests.get(f"http://{ip}", timeout=0.5)
                alive.append(ip)
            except Exception:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.3)
                    if s.connect_ex((ip, 80)) == 0:
                        alive.append(ip)
                    s.close()
                except Exception:
                    pass
        if alive:
            return f"Alive hosts: {alive}"
        return f"No hosts found on {subnet}.0/24 (first 19 checked)"
    except Exception as e:
        return f"Network scan error: {e}"

def _get_local_subnet():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return ".".join(local_ip.split(".")[:3])
    except Exception:
        return "192.168.1"

def _check_firewall():
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout[:1500] if result.stdout else "Could not check firewall"
    except Exception as e:
        return f"Firewall check error: {e}"

def _check_windows_updates():
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 | Format-Table HotFixID,Description,InstalledOn -AutoSize"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout[:1500] if result.stdout else "Could not check updates"
    except Exception as e:
        return f"Update check error: {e}"

def _malware_scan(params):
    path = params.get("path", "C:\\Users")
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-ChildItem '{path}' -Recurse -Include *.exe,*.dll,*.bat,*.ps1 -ErrorAction SilentlyContinue | Select-Object -First 50 FullName,Length,LastWriteTime | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout[:2000] if result.stdout else "No files found"
        return f"File scan of {path}:\n{output}"
    except Exception as e:
        return f"Scan error: {e}"

def _check_weak_passwords():
    try:
        result = subprocess.run(
            ["net", "user"],
            capture_output=True, text=True, timeout=10
        )
        users = result.stdout
        return f"Local users:\n{users}\n\nNote: Password strength cannot be checked remotely. Use a password manager."
    except Exception as e:
        return f"Password check error: {e}"

def _check_active_connections():
    try:
        result = subprocess.run(
            ["netstat", "-an"],
            capture_output=True, text=True, timeout=10
        )
        established = [l for l in result.stdout.split("\n") if "ESTABLISHED" in l]
        return f"Active connections: {len(established)}\n" + "\n".join(established[:20])
    except Exception as e:
        return f"Connection check error: {e}"

def _check_ssl(params):
    domain = params.get("domain", "")
    if not domain:
        return "Domain required"
    try:
        import requests
        r = requests.get(f"https://{domain}", timeout=10, verify=True)
        cert = r.headers.get("Server", "unknown")
        return f"SSL check {domain}: accessible, server={cert}, status={r.status_code}"
    except requests.exceptions.SSLError as e:
        return f"SSL error for {domain}: {e}"
    except Exception as e:
        return f"SSL check error: {e}"

def _log_event(params):
    logs = _load_log()
    event = {
        "type": params.get("type", "info"),
        "message": params.get("message", ""),
        "severity": params.get("severity", "low"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    logs.append(event)
    _save_log(logs)
    return f"Event logged: {event['type']} - {event['message']}"

def _security_report():
    logs = _load_log()
    recent = logs[-20:]
    if not recent:
        return "No security events logged"
    lines = []
    for e in recent:
        lines.append(f"[{e['severity']}] {e['timestamp']} - {e['type']}: {e['message']}")
    return f"Security report ({len(recent)} events):\n" + "\n".join(lines)

def _security_status():
    logs = _load_log()
    return f"Security: {len(logs)} events logged. Use security_report for details."

def _load_log():
    try:
        if _SECURITY_LOG.exists():
            return json.loads(_SECURITY_LOG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_log(logs):
    _SECURITY_LOG.write_text(json.dumps(logs[-500:], indent=2, default=str), encoding="utf-8")

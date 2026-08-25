"""Cybersecurity and ethical hacking educational tools.
All tools are for defensive security and educational purposes only.
Wraps standard security tools (nmap, netsh, powershell) for learning."""

import subprocess
import os
import json
import hashlib
import re
from pathlib import Path


def _run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode, r.stderr.strip()
    except Exception as e:
        return str(e), 1, ""


def _check_tool(name):
    out, code, _ = _run(["where", name] if os.name == "nt" else ["which", name])
    return code == 0 and out.strip()


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "help")
    target = params.get("target", "")
    value = params.get("value", "")

    handlers = {
        "port_scan": lambda: _port_scan(target),
        "network_info": _network_info,
        "wifi_security": _wifi_security,
        "system_audit": _system_audit,
        "password_check": lambda: _password_check(target),
        "hash_file": lambda: _hash_file(target),
        "open_ports": lambda: _open_ports(target),
        "firewall_status": _firewall_status,
        "running_services": _running_services,
        "installed_software": _installed_software,
        "env_secrets_check": _env_secrets_check,
        "credential_check": _credential_check,
        "dns_lookup": lambda: _dns_lookup(target),
        "whois_lookup": lambda: _whois_lookup(target),
        "mac_lookup": lambda: _mac_lookup(target),
        "network_connections": _network_connections,
        "arp_table": _arp_table,
        "traceroute": lambda: _traceroute(target),
        "wifi_passwords": _wifi_passwords,
        "user_accounts": _user_accounts,
        "file_permissions": lambda: _file_permissions(target),
        "startup_programs": _startup_programs,
        "scheduled_tasks": _scheduled_tasks,
        "browser_history_check": _browser_history_check,
        "encryption_info": _encryption_info,
        "vulnerability_check": _vulnerability_check,
        "help": _help,
    }

    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _help():
    return """CYBERSECURITY TOOLS (Educational/Defensive):
  port_scan        - Scan ports on target (e.g. 192.168.1.1)
  open_ports       - Quick check common ports on target
  network_info     - Show local network configuration
  wifi_security    - Analyze WiFi security settings
  system_audit     - Full system security audit
  password_check   - Check password strength
  hash_file        - Generate file hash (MD5/SHA256)
  firewall_status  - Check firewall configuration
  running_services - List running services
  installed_software - List installed programs
  env_secrets_check - Check for exposed secrets in env
  credential_check - Check for weak/default credentials
  dns_lookup       - DNS resolution check
  whois_lookup     - WHOIS domain information
  mac_lookup       - MAC address vendor lookup
  network_connections - Active network connections
  arp_table        - ARP cache contents
  traceroute       - Network route to target
  wifi_passwords   - Show saved WiFi passwords
  user_accounts    - List local user accounts
  file_permissions - Check file/folder permissions
  startup_programs - List startup programs
  scheduled_tasks  - List scheduled tasks
  browser_history_check - Check browser history location
  encryption_info  - Show encryption status
  vulnerability_check - Basic vulnerability scan"""


def _port_scan(target):
    if not target:
        return "Provide target IP or hostname (e.g. 192.168.1.1)"
    if _check_tool("nmap"):
        out, code, err = _run(["nmap", "-sV", "-T4", "--top-ports", "100", target], timeout=60)
        return f"NMAP SCAN of {target}:\n{out}" if out else f"Nmap error: {err}"
    common_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3389, 5900, 8080]
    import socket
    open_ports = []
    for port in common_ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((target, port))
            if result == 0:
                services = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
                           80: "HTTP", 110: "POP3", 135: "RPC", 139: "NetBIOS", 143: "IMAP",
                           443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
                           1723: "PPTP", 3389: "RDP", 5900: "VNC", 8080: "HTTP-Proxy"}
                open_ports.append(f"  PORT {port}: OPEN ({services.get(port, 'unknown')})")
            s.close()
        except Exception:
            pass
    return f"PORT SCAN of {target}:\n" + ("\n".join(open_ports) if open_ports else "  No common ports open")


def _open_ports(target):
    if not target:
        target = "127.0.0.1"
    return _port_scan(target)


def _network_info():
    out, _, _ = _run(["ipconfig", "/all"])
    return f"NETWORK CONFIGURATION:\n{out[:3000]}" if out else "Could not get network info"


def _wifi_security():
    out, _, _ = _run(["netsh", "wlan", "show", "profiles"])
    profiles = []
    for line in out.split("\n"):
        if "All User Profile" in line:
            name = line.split(":")[-1].strip()
            if name:
                profiles.append(name)
    results = [f"WiFi Profiles Found: {len(profiles)}"]
    for p in profiles[:5]:
        detail, _, _ = _run(["netsh", "wlan", "show", "profile", f"name={p}", "key=clear"])
        auth = "unknown"
        for line in detail.split("\n"):
            if "Authentication" in line:
                auth = line.split(":")[-1].strip()
            if "Key Content" in line:
                results.append(f"  {p}: Auth={auth}, Password={line.split(':')[-1].strip()}")
                break
        else:
            results.append(f"  {p}: Auth={auth}, No password saved")
    return "\n".join(results)


def _system_audit():
    checks = []
    # Check Windows Update
    out, _, _ = _run(["powershell", "-Command",
                      "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 1 InstalledOn,HotFixID | Format-List"], timeout=10)
    checks.append(f"LATEST UPDATE:\n{out}" if out else "Could not check updates")
    # Check firewall
    out, _, _ = _run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    checks.append(f"FIREWALL:\n{out}" if out else "Could not check firewall")
    # Check defender
    out, _, _ = _run(["powershell", "-Command",
                      "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AntivirusEnabled,LastScanTime | Format-List"], timeout=10)
    checks.append(f"DEFENDER:\n{out}" if out else "Could not check Defender")
    # Check UAC
    out, _, _ = _run(["reg", "query",
                      "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "/v", "EnableLUA"])
    checks.append(f"UAC:\n{out}" if out else "Could not check UAC")
    # Check SMB
    out, _, _ = _run(["powershell", "-Command",
                      "Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol,EnableSMB2Protocol | Format-List"], timeout=10)
    checks.append(f"SMB:\n{out}" if out else "Could not check SMB")
    return "SYSTEM SECURITY AUDIT:\n" + "\n\n".join(checks)


def _password_check(password):
    if not password:
        return "Provide a password to check (target=yourpassword)"
    score = 0
    feedback = []
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Too short (min 8 chars)")
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    if re.search(r"[a-z]", password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    if re.search(r"\d", password):
        score += 1
    else:
        feedback.append("Add numbers")
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
    else:
        feedback.append("Add special characters")
    if len(password) >= 16:
        score += 1
    strength = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong", "Excellent"][min(score, 6)]
    return f"Password Strength: {strength} ({score}/7)\n" + "\n".join(feedback) if feedback else f"Password Strength: {strength} ({score}/7) - Good job!"


def _hash_file(filepath):
    if not filepath or not os.path.exists(filepath):
        return f"File not found: {filepath}"
    try:
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
        return f"FILE HASHES for {filepath}:\n  MD5:    {md5.hexdigest()}\n  SHA1:   {sha1.hexdigest()}\n  SHA256: {sha256.hexdigest()}"
    except Exception as e:
        return f"Error hashing file: {e}"


def _firewall_status():
    out, _, _ = _run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    return f"FIREWALL STATUS:\n{out}" if out else "Could not check firewall"


def _running_services():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 30 Name,DisplayName | Format-Table -AutoSize"], timeout=10)
    return f"RUNNING SERVICES:\n{out}" if out else "Could not list services"


def _installed_software():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object -First 20 DisplayName,DisplayVersion | Format-Table -AutoSize"], timeout=10)
    return f"INSTALLED SOFTWARE:\n{out}" if out else "Could not list software"


def _env_secrets_check():
    sensitive = ["password", "secret", "key", "token", "api", "credential", "auth", "private"]
    found = []
    for key, val in os.environ.items():
        if any(s in key.lower() for s in sensitive):
            masked = val[:4] + "****" if len(val) > 4 else "****"
            found.append(f"  {key} = {masked}")
    return f"SENSITIVE ENV VARS ({len(found)} found):\n" + "\n".join(found) if found else "No sensitive env vars found"


def _credential_check():
    default_creds = [
        ("admin", "admin"), ("admin", "password"), ("root", "root"),
        ("admin", "1234"), ("user", "user"), ("test", "test"),
    ]
    return f"""CREDENTIAL SECURITY CHECK:
  Default credential pairs to audit against: {len(default_creds)}
  Check: Are any services running with default credentials?
  Recommendation: Change all default passwords immediately
  Use strong passwords (16+ chars, mixed case, numbers, symbols)
  
  Common weak passwords to avoid:
  - password, 123456, admin, letmein, welcome
  - Your name, birthday, or pet names"""


def _dns_lookup(target):
    if not target:
        return "Provide a hostname to lookup (target=example.com)"
    out, _, _ = _run(["nslookup", target], timeout=10)
    return f"DNS LOOKUP for {target}:\n{out}" if out else "DNS lookup failed"


def _whois_lookup(target):
    if not target:
        return "Provide a domain (target=example.com)"
    if _check_tool("whois"):
        out, _, _ = _run(["whois", target], timeout=15)
        return f"WHOIS for {target}:\n{out[:2000]}" if out else "WHOIS failed"
    return f"WHOIS tool not installed. Install whois or use: nslookup {target}"


def _mac_lookup(target):
    if not target:
        return "Provide a MAC address (target=00:1A:2B:3C:4D:5E)"
    return f"MAC LOOKUP: {target}\n  Use https://macvendors.com to look up this MAC address vendor"


def _network_connections():
    out, _, _ = _run(["netstat", "-ano"], timeout=10)
    lines = [l for l in out.split("\n") if "ESTABLISHED" in l][:30]
    return f"ACTIVE CONNECTIONS ({len(lines)}):\n" + "\n".join(lines) if lines else "No active connections found"


def _arp_table():
    out, _, _ = _run(["arp", "-a"])
    return f"ARP TABLE:\n{out[:2000]}" if out else "Could not get ARP table"


def _traceroute(target):
    if not target:
        return "Provide a target (target=8.8.8.8)"
    out, _, _ = _run(["tracert", "-d", "-h", "10", target], timeout=30)
    return f"TRACEROUTE to {target}:\n{out}" if out else "Traceroute failed"


def _wifi_passwords():
    out, _, _ = _run(["netsh", "wlan", "show", "profiles"])
    profiles = []
    for line in out.split("\n"):
        if "All User Profile" in line:
            name = line.split(":")[-1].strip()
            if name:
                profiles.append(name)
    results = [f"Saved WiFi Networks: {len(profiles)}"]
    for p in profiles[:10]:
        detail, _, _ = _run(["netsh", "wlan", "show", "profile", f"name={p}", "key=clear"])
        for line in detail.split("\n"):
            if "Key Content" in line:
                pw = line.split(":")[-1].strip()
                results.append(f"  {p}: {pw}")
                break
        else:
            results.append(f"  {p}: (no saved password)")
    return "\n".join(results)


def _user_accounts():
    out, _, _ = _run(["net", "user"])
    return f"USER ACCOUNTS:\n{out}" if out else "Could not list users"


def _file_permissions(filepath):
    if not filepath or not os.path.exists(filepath):
        return f"File not found: {filepath}"
    out, _, _ = _run(["icacls", filepath])
    return f"PERMISSIONS for {filepath}:\n{out}" if out else "Could not check permissions"


def _startup_programs():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-Table -AutoSize"], timeout=10)
    return f"STARTUP PROGRAMS:\n{out}" if out else "Could not list startup programs"


def _scheduled_tasks():
    out, _, _ = _run(["powershell", "-Command",
                      "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object -First 20 TaskName,State | Format-Table -AutoSize"], timeout=10)
    return f"SCHEDULED TASKS:\n{out}" if out else "Could not list scheduled tasks"


def _browser_history_check():
    chrome_path = Path.home() / "AppData/Local/Google/Chrome/User Data/Default/History"
    edge_path = Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/History"
    firefox_path = Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles"
    locations = []
    if chrome_path.exists():
        locations.append(f"Chrome: {chrome_path} ({chrome_path.stat().st_size / 1024 / 1024:.1f} MB)")
    if edge_path.exists():
        locations.append(f"Edge: {edge_path} ({edge_path.stat().st_size / 1024 / 1024:.1f} MB)")
    if firefox_path.exists():
        locations.append(f"Firefox: {firefox_path}")
    return "BROWSER HISTORY LOCATIONS:\n" + "\n".join(locations) if locations else "No browser history found (browsers may not be installed)"


def _encryption_info():
    out, _, _ = _run(["manage-bde", "-status", "C:"], timeout=10)
    if "BitLocker" in out:
        return f"BITLOCKER STATUS:\n{out}"
    return "BitLocker not available or drive not encrypted.\nUse Settings > Privacy & Security > Device Encryption to enable."


def _vulnerability_check():
    checks = []
    # SMBv1
    out, _, _ = _run(["powershell", "-Command",
                      "Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol"], timeout=10)
    if "True" in out:
        checks.append("  [CRITICAL] SMBv1 is ENABLED - disable it immediately")
    else:
        checks.append("  [OK] SMBv1 is disabled")
    # Remote Desktop
    out, _, _ = _run(["powershell", "-Command",
                      "Get-ItemProperty 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections -ErrorAction SilentlyContinue"], timeout=10)
    if "fDenyTSConnections" in out and "0" in out:
        checks.append("  [WARNING] Remote Desktop is ENABLED")
    else:
        checks.append("  [OK] Remote Desktop is disabled")
    # Default admin
    out, _, _ = _run(["net", "user", "Administrator"])
    if "Account active" in out.lower():
        checks.append("  [WARNING] Default Administrator account is active")
    # Guest account
    out, _, _ = _run(["net", "user", "Guest"])
    if "account active" in out.lower():
        checks.append("  [WARNING] Guest account is active")
    # UAC
    out, _, _ = _run(["reg", "query",
                      "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "/v", "EnableLUA"])
    if "0x1" in out:
        checks.append("  [OK] UAC is enabled")
    else:
        checks.append("  [WARNING] UAC may be disabled")
    return "VULNERABILITY SCAN:\n" + "\n".join(checks)

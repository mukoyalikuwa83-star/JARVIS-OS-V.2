"""Smart assistant — workflow suggestions, file search, daily reports, quick actions."""

import json
import os
import time
import subprocess
from pathlib import Path
from collections import Counter


_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / ".jarvis"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _suggest_workflows() -> str:
    """Analyze learned patterns and suggest workflow shortcuts."""
    patterns_file = _MEMORY_DIR / "learned_patterns.json"
    patterns = _load_json(patterns_file)

    if not patterns:
        return "SUGGESTIONS|No patterns learned yet. Use JARVIS more and I'll start suggesting shortcuts."

    suggestions = []
    for key, data in patterns.items():
        count = data.get("count", 0)
        if count >= 3:
            action = key.split(":")[0] if ":" in key else key
            ctx = key.split(":")[1] if ":" in key else ""
            last = data.get("last_seen", "?")
            suggestions.append(f"  - You often use {action} ({count}x). I can create a workflow for this. (last: {last})")

    if not suggestions:
        return "SUGGESTIONS|Not enough repeated patterns yet. Keep using JARVIS!"

    top = sorted(patterns.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:5]
    lines = [f"  {i+1}. {k}: used {v.get('count', 0)}x (last: {v.get('last_seen', '?')})" for i, (k, v) in enumerate(top)]
    return f"SMART SUGGESTIONS ({len(suggestions)} patterns found):\n" + "\n".join(lines)


def _search_files(params: dict) -> str:
    """Search for files on the system."""
    query = str(params.get("query", "") or "").strip()
    directory = str(params.get("directory", "") or "").strip()
    max_results = int(params.get("max_results", 20) or 20)
    file_type = str(params.get("file_type", "") or "").strip().lower()

    if not query and not file_type:
        return "ERROR: Provide a query or file_type."

    search_dir = Path(directory) if directory else Path.home()
    if not search_dir.exists():
        return f"ERROR: Directory '{directory}' not found."

    results = []
    try:
        for item in search_dir.rglob("*"):
            if len(results) >= max_results:
                break
            if item.is_file():
                name = item.name.lower()
                match = False
                if query and query.lower() in name:
                    match = True
                if file_type and item.suffix.lower() == f".{file_type.lstrip('.')}":
                    match = True
                if match:
                    size = item.stat().st_size
                    mod = time.strftime("%Y-%m-%d %H:%M", time.localtime(item.stat().st_mtime))
                    if size > 1024 * 1024:
                        size_str = f"{size // (1024*1024)}MB"
                    elif size > 1024:
                        size_str = f"{size // 1024}KB"
                    else:
                        size_str = f"{size}B"
                    results.append(f"  {item.name} ({size_str}, {mod}) — {item.parent}")
    except PermissionError:
        pass
    except Exception as e:
        return f"SEARCH_ERROR|{e}"

    if not results:
        return f"SEARCH_EMPTY|No files matching '{query or file_type}' in {search_dir}"
    return f"SEARCH RESULTS ({len(results)}):\n" + "\n".join(results)


def _generate_report() -> str:
    """Generate a daily activity report from learned patterns."""
    patterns_file = _MEMORY_DIR / "learned_patterns.json"
    patterns = _load_json(patterns_file)

    notifs_file = _MEMORY_DIR / "notifications.json"
    try:
        notifs = json.loads(notifs_file.read_text(encoding="utf-8"))
    except Exception:
        notifs = []

    ctx_file = _MEMORY_DIR / "active_context.json"
    ctx = _load_json(ctx_file)

    total_actions = sum(d.get("count", 0) for d in patterns.values())
    tool_counts = Counter()
    error_count = 0
    for key, data in patterns.items():
        action = key.split(":")[0] if ":" in key else key
        tool_counts[action] += data.get("count", 0)
        results = data.get("results", {})
        error_count += results.get("error", 0)

    top_tools = tool_counts.most_common(10)
    lines = []
    lines.append(f"TOTAL ACTIONS: {total_actions}")
    lines.append(f"ERRORS: {error_count}")
    lines.append(f"SUCCESS RATE: {((total_actions - error_count) / max(total_actions, 1) * 100):.0f}%")
    lines.append("")
    lines.append("TOP TOOLS:")
    for tool, count in top_tools:
        lines.append(f"  {tool}: {count}x")

    if ctx:
        lines.append("")
        lines.append("CONTEXT:")
        for k, v in ctx.items():
            lines.append(f"  {k}: {v.get('value', '?')}")

    unread = [n for n in notifs if isinstance(n, dict) and not n.get("read")]
    if unread:
        lines.append("")
        lines.append(f"UNREAD NOTIFICATIONS: {len(unread)}")

    return "DAILY REPORT:\n" + "\n".join(lines)


def _quick_action(params: dict) -> str:
    """Execute a quick predefined action."""
    action = str(params.get("action_name", "") or "").strip().lower()

    quick_actions = {
        "screenshot": lambda: _run_ps("Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds"),
        "battery": lambda: _run_ps("(Get-WmiObject Win32_Battery).EstimatedChargeRemaining"),
        "wifi": lambda: _run_ps("(netsh wlan show interfaces) | Select-String 'SSID|Signal|State'"),
        "disk_space": lambda: _run_ps("Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}},@{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}}"),
        "running_apps": lambda: _run_ps("Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object ProcessName,MainWindowTitle | Format-Table -AutoSize"),
        "ip": lambda: _run_ps("(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content"),
        "uptime": lambda: _run_ps("(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object Days,Hours,Minutes"),
        "temp_files": lambda: _run_ps("(Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB"),
    }

    if action == "list":
        return "QUICK ACTIONS:\n" + "\n".join(f"  {k}" for k in sorted(quick_actions.keys()))

    if action not in quick_actions:
        return f"Unknown action: {action}. Use action='list' to see available."

    result = quick_actions[action]()
    return f"QUICK_ACTION|{action}:\n{result}"


def _run_ps(cmd: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return r.stdout.strip()[:2000] if r.stdout.strip() else r.stderr.strip()[:500]
    except Exception as e:
        return str(e)


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "suggest") or "suggest").lower()

    if action == "suggest":
        return _suggest_workflows()
    elif action == "search":
        return _search_files(params)
    elif action == "report":
        return _generate_report()
    elif action == "quick":
        return _quick_action(params)
    return f"Unknown action: {action}. Valid: suggest, search, report, quick"

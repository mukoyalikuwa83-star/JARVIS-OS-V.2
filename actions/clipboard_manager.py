"""Clipboard manager — history, snippets, auto-copy, clipboard monitoring."""

import json
import time
import subprocess
import os
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / ".jarvis"
_CLIPBOARD_FILE = _MEMORY_DIR / "clipboard_history.json"
_SNIPPETS_FILE = _MEMORY_DIR / "snippets.json"


def _load_json(path: Path) -> list | dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [] if "clip" in path.name else {}


def _save_json(path: Path, data):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_clipboard_windows() -> str:
    """Get clipboard content on Windows via PowerShell."""
    try:
        r = subprocess.run(
            ["powershell", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _set_clipboard_windows(text: str) -> bool:
    """Set clipboard content on Windows via PowerShell."""
    try:
        escaped = text.replace("'", "''")
        subprocess.run(
            ["powershell", "-Command", f"Set-Clipboard -Value '{escaped}'"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def get_clipboard(params: dict) -> str:
    """Get current clipboard content."""
    content = _get_clipboard_windows()
    if not content:
        return "CLIPBOARD_EMPTY|Nothing in clipboard."

    history = _load_json(_CLIPBOARD_FILE)
    if not isinstance(history, list):
        history = []

    if not history or history[-1].get("text") != content:
        history.append({
            "text": content[:5000],
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if len(history) > 100:
            history = history[-100:]
        _save_json(_CLIPBOARD_FILE, history)

    preview = content[:200] + "..." if len(content) > 200 else content
    return f"CLIPBOARD|{len(content)} chars:\n{preview}"


def set_clipboard(params: dict) -> str:
    """Set clipboard content."""
    text = str(params.get("text", "") or "").strip()
    if not text:
        return "ERROR: Provide text to copy."
    if _set_clipboard_windows(text):
        return f"CLIPBOARD_SET|{len(text)} chars copied."
    return "CLIPBOARD_FAILED|Could not set clipboard."


def get_history(params: dict) -> str:
    """Get clipboard history."""
    limit = int(params.get("limit", 10) or 10)
    history = _load_json(_CLIPBOARD_FILE)
    if not isinstance(history, list) or not history:
        return "No clipboard history."

    items = history[-limit:]
    lines = []
    for i, item in enumerate(reversed(items)):
        text = item.get("text", "")[:80]
        t = item.get("time", "?")
        lines.append(f"  {i+1}. [{t}] {text}")
    return f"CLIPBOARD HISTORY ({len(items)}):\n" + "\n".join(lines)


def copy_last(params: dict) -> str:
    """Copy a specific history item back to clipboard."""
    index = int(params.get("index", 1) or 1)
    history = _load_json(_CLIPBOARD_FILE)
    if not isinstance(history, list):
        return "No clipboard history."

    idx = len(history) - index
    if 0 <= idx < len(history):
        text = history[idx].get("text", "")
        if _set_clipboard_windows(text):
            return f"CLIPBOARD_RESTORED|Restored item #{index}: {text[:80]}"
        return "CLIPBOARD_FAILED|Could not restore."
    return f"Invalid index {index}. History has {len(history)} items."


def save_snippet(params: dict) -> str:
    """Save a text snippet for quick access."""
    name = str(params.get("name", "") or "").strip()
    text = str(params.get("text", "") or "").strip()
    if not name or not text:
        return "ERROR: Provide name and text."
    snippets = _load_json(_SNIPPETS_FILE)
    if not isinstance(snippets, dict):
        snippets = {}
    snippets[name] = {
        "text": text,
        "created": time.strftime("%Y-%m-%d %H:%M"),
    }
    _save_json(_SNIPPETS_FILE, snippets)
    return f"SNIPPET_SAVED|{name} ({len(text)} chars)"


def get_snippet(params: dict) -> str:
    """Get and copy a snippet to clipboard."""
    name = str(params.get("name", "") or "").strip()
    if not name:
        return "ERROR: Provide snippet name."
    snippets = _load_json(_SNIPPETS_FILE)
    if not isinstance(snippets, dict):
        return "No snippets saved."
    snippet = snippets.get(name)
    if not snippet:
        return f"Snippet '{name}' not found."
    text = snippet.get("text", "")
    _set_clipboard_windows(text)
    return f"SNIPPET|{name}: {text[:200]}"


def list_snippets(params: dict) -> str:
    """List all saved snippets."""
    snippets = _load_json(_SNIPPETS_FILE)
    if not isinstance(snippets, dict) or not snippets:
        return "No snippets saved."
    lines = [f"  {name}: {s.get('text', '')[:50]} ({s.get('created', '?')})" for name, s in snippets.items()]
    return f"SNIPPETS ({len(snippets)}):\n" + "\n".join(lines)


def delete_snippet(params: dict) -> str:
    """Delete a snippet."""
    name = str(params.get("name", "") or "").strip()
    snippets = _load_json(_SNIPPETS_FILE)
    if not isinstance(snippets, dict):
        return "No snippets."
    if name in snippets:
        del snippets[name]
        _save_json(_SNIPPETS_FILE, snippets)
        return f"SNIPPET_DELETED|{name}"
    return f"Snippet '{name}' not found."


def clear_history(params: dict) -> str:
    """Clear clipboard history."""
    _save_json(_CLIPBOARD_FILE, [])
    return "CLIPBOARD_HISTORY_CLEARED"


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "get") or "get").lower()

    if action == "get":
        return get_clipboard(params)
    elif action == "set":
        return set_clipboard(params)
    elif action == "history":
        return get_history(params)
    elif action == "copy_last":
        return copy_last(params)
    elif action == "save_snippet":
        return save_snippet(params)
    elif action == "get_snippet":
        return get_snippet(params)
    elif action == "list_snippets":
        return list_snippets(params)
    elif action == "delete_snippet":
        return delete_snippet(params)
    elif action == "clear":
        return clear_history(params)
    return f"Unknown action: {action}. Valid: get, set, history, copy_last, save_snippet, get_snippet, list_snippets, delete_snippet, clear"

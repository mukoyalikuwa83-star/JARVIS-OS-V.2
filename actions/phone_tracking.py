"""
Phone Call Tracking Module for JARVIS.
Track calls, log conversations, record duration, manage contacts.
Requires: none (uses local storage)
"""
import os
import time
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)
_CALL_LOG = _DATA_DIR / "call_log.json"
_CONTACTS = _DATA_DIR / "contacts.json"

def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    
    if action == "log_call":
        return _log_call(params)
    elif action == "get_calls":
        return _get_calls(params)
    elif action == "add_contact":
        return _add_contact(params)
    elif action == "get_contacts":
        return _get_contacts()
    elif action == "search_contact":
        return _search_contact(params)
    elif action == "call_stats":
        return _call_stats()
    elif action == "delete_contact":
        return _delete_contact(params)
    elif action == "export":
        return _export_log()
    else:
        return "Phone: log_call|get_calls|add_contact|get_contacts|search_contact|call_stats|delete_contact|export"

def _load_log():
    try:
        if _CALL_LOG.exists():
            return json.loads(_CALL_LOG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_log(calls):
    _CALL_LOG.write_text(json.dumps(calls, indent=2, default=str), encoding="utf-8")

def _log_call(params):
    calls = _load_log()
    entry = {
        "id": str(int(time.time() * 1000))[-10:],
        "number": params.get("number", ""),
        "contact": params.get("contact", "Unknown"),
        "direction": params.get("direction", "outgoing"),
        "duration_seconds": params.get("duration", 0),
        "status": params.get("status", "completed"),
        "notes": params.get("notes", ""),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
    }
    calls.append(entry)
    _save_log(calls)
    return f"Call logged: {entry['contact']} ({entry['direction']}) {entry['duration_seconds']}s"

def _get_calls(params):
    calls = _load_log()
    limit = params.get("limit", 20)
    recent = calls[-limit:]
    if not recent:
        return "No calls logged"
    lines = []
    for c in recent:
        lines.append(f"{c['timestamp']} | {c['contact']} | {c['direction']} | {c['duration_seconds']}s | {c['status']}")
    return "\n".join(lines)

def _add_contact(params):
    contacts = _load_contacts()
    name = params.get("name", "").strip()
    number = params.get("number", "").strip()
    if not name or not number:
        return "Name and number required"
    contacts.append({
        "name": name,
        "number": number,
        "email": params.get("email", ""),
        "notes": params.get("notes", ""),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    _save_contacts(contacts)
    return f"Contact added: {name} ({number})"

def _get_contacts():
    contacts = _load_contacts()
    if not contacts:
        return "No contacts"
    lines = []
    for c in contacts:
        lines.append(f"{c['name']} | {c['number']} | {c.get('email', '')}")
    return "\n".join(lines)

def _search_contact(params):
    contacts = _load_contacts()
    query = params.get("name", "").lower()
    matches = [c for c in contacts if query in c["name"].lower()]
    if not matches:
        return f"No contacts matching '{query}'"
    lines = []
    for c in matches:
        lines.append(f"{c['name']} | {c['number']}")
    return "\n".join(lines)

def _delete_contact(params):
    contacts = _load_contacts()
    name = params.get("name", "").lower()
    before = len(contacts)
    contacts = [c for c in contacts if name not in c["name"].lower()]
    if len(contacts) == before:
        return f"No contacts matching '{name}'"
    _save_contacts(contacts)
    return f"Deleted {before - len(contacts)} contact(s)"

def _call_stats():
    calls = _load_log()
    if not calls:
        return "No call data"
    total = len(calls)
    total_dur = sum(c.get("duration_seconds", 0) for c in calls)
    outgoing = sum(1 for c in calls if c.get("direction") == "outgoing")
    incoming = total - outgoing
    avg_dur = total_dur / total if total else 0
    return f"Calls: {total} total ({outgoing} out, {incoming} in), Total: {total_dur}s, Avg: {avg_dur:.0f}s"

def _export_log():
    calls = _load_log()
    return json.dumps(calls, indent=2, default=str)[:3000]

def _load_contacts():
    try:
        if _CONTACTS.exists():
            return json.loads(_CONTACTS.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_contacts(contacts):
    _CONTACTS.write_text(json.dumps(contacts, indent=2, default=str), encoding="utf-8")

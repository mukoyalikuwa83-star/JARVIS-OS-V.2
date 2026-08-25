"""Contact management: store, search, update contacts."""

import json
import os
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_CONTACTS_FILE = _BASE_DIR / ".jarvis" / "contacts.json"


def _load_contacts():
    try:
        return json.loads(_CONTACTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_contacts(contacts):
    _CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONTACTS_FILE.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")


def add_contact(params=None):
    contacts = _load_contacts()
    name = (params or {}).get("name", "").strip()
    if not name:
        return json.dumps({"error": "Name is required."})
    phone = (params or {}).get("phone", "")
    email = (params or {}).get("email", "")
    platform = (params or {}).get("platform", "")
    relationship = (params or {}).get("relationship", "")
    notes = (params or {}).get("notes", "")
    contact = {
        "name": name, "phone": phone, "email": email,
        "platform": platform, "relationship": relationship,
        "notes": notes, "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    existing_idx = next((i for i, c in enumerate(contacts) if c.get("name", "").lower() == name.lower()), -1)
    if existing_idx >= 0:
        contacts[existing_idx].update({k: v for k, v in contact.items() if v})
        contacts[existing_idx]["updated"] = datetime.now().isoformat()
    else:
        contacts.append(contact)
    _save_contacts(contacts)
    action = "updated" if existing_idx >= 0 else "added"
    return json.dumps({"result": f"Contact {action}: {name}", "total_contacts": len(contacts)})


def search_contacts(params=None):
    contacts = _load_contacts()
    query = (params or {}).get("query", "").lower().strip()
    if not query:
        return json.dumps({"contacts": contacts, "total": len(contacts)})
    results = [c for c in contacts if query in c.get("name", "").lower()
               or query in c.get("phone", "").lower()
               or query in c.get("email", "").lower()
               or query in c.get("relationship", "").lower()
               or query in c.get("notes", "").lower()]
    return json.dumps({"contacts": results, "total": len(results), "query": query})


def delete_contact(params=None):
    contacts = _load_contacts()
    name = (params or {}).get("name", "").strip()
    if not name:
        return json.dumps({"error": "Name is required."})
    new_contacts = [c for c in contacts if c.get("name", "").lower() != name.lower()]
    if len(new_contacts) == len(contacts):
        return json.dumps({"error": f"Contact '{name}' not found."})
    _save_contacts(new_contacts)
    return json.dumps({"result": f"Deleted contact: {name}", "remaining": len(new_contacts)})


def list_all(params=None):
    contacts = _load_contacts()
    summary = [{"name": c.get("name"), "phone": c.get("phone"), "platform": c.get("platform"),
                "relationship": c.get("relationship")} for c in contacts]
    return json.dumps({"contacts": summary, "total": len(summary)})


ACTIONS = {
    "add": add_contact,
    "search": search_contacts,
    "delete": delete_contact,
    "list": list_all,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "list")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})

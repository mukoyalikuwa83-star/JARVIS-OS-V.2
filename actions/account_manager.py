"""Account Manager — saves/loads login details for side hustle platforms."""
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_ACCOUNTS_FILE = _DATA_DIR / "accounts.json"


def _load():
    try:
        if _ACCOUNTS_FILE.exists():
            return json.loads(_ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(data):
    _DATA_DIR.mkdir(exist_ok=True)
    _ACCOUNTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_account(platform: str, email: str, password: str, username: str = "", notes: str = "") -> str:
    """Save login credentials for a platform. Passwords stored locally only."""
    accounts = _load()
    accounts[platform] = {
        "email": email,
        "password": password,
        "username": username,
        "notes": notes,
        "saved_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save(accounts)
    return f"Saved {platform} account ({email})"


def get_account(platform: str) -> dict:
    """Get saved login details for a platform."""
    return _load().get(platform, {})


def list_accounts() -> str:
    """List all saved platform accounts."""
    accounts = _load()
    if not accounts:
        return "No accounts saved."
    lines = ["=== SAVED ACCOUNTS ==="]
    for plat, info in accounts.items():
        lines.append(f"  {plat}: {info.get('email', 'no email')} (saved {info.get('saved_at', 'unknown')})")
    return "\n".join(lines)


def delete_account(platform: str) -> str:
    """Delete saved account for a platform."""
    accounts = _load()
    if platform in accounts:
        del accounts[platform]
        _save(accounts)
        return f"Deleted {platform} account"
    return f"No {platform} account found"


def handle(params: dict) -> str:
    action = params.get("action", "list")
    if action == "save":
        return save_account(
            params.get("platform", ""),
            params.get("email", ""),
            params.get("password", ""),
            params.get("username", ""),
            params.get("notes", ""),
        )
    elif action == "get":
        acct = get_account(params.get("platform", ""))
        if acct:
            return f"Account: {acct.get('email', '?')} / {acct.get('password', '?')}"
        return "No account found."
    elif action == "list":
        return list_accounts()
    elif action == "delete":
        return delete_account(params.get("platform", ""))
    return f"Unknown action: {action}. Use: save, get, list, delete"

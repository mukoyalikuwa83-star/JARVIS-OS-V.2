"""JARVIS asset & capability inventory.

Builds a live 'what JARVIS has' brief from disk state so the model always
knows its accounts, products, earnings, pending work, and physical toolkits.
Kept concise so it stays under the model's context budget.
"""

import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DATA = _BASE / ".jarvis"


def _read_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _accounts_brief():
    d = _read_json(_DATA / "worker_accounts.json", {})
    if isinstance(d, dict) and d:
        active = [k for k, v in d.items() if isinstance(v, dict) and v.get("status") == "active"]
        needs = [k for k, v in d.items() if isinstance(v, dict) and v.get("status") == "needs_human_signup"]
        out = []
        if active:
            out.append("Active: " + ", ".join(active))
        if needs:
            out.append("Need human signup: " + ", ".join(needs))
        return "; ".join(out) if out else "No accounts configured"
    return "No accounts configured"


def _products_brief():
    d = _read_json(_DATA / "worker_jobs.json", {})
    delivered = d.get("delivered", []) if isinstance(d, dict) else []
    pending = d.get("pending", []) if isinstance(d, dict) else []
    total_val = 0
    for job in delivered:
        try:
            total_val += float((job.get("listing") or {}).get("price", 0))
        except Exception:
            pass
    return f"{len(delivered)} products delivered (~${total_val:,.0f} value), {len(pending)} pending"


def _earnings_brief():
    d = _read_json(_DATA / "earnings.json", {})
    entries = d.get("entries", []) if isinstance(d, dict) else []
    total = 0
    for e in entries:
        try:
            total += float(e.get("amount", 0))
        except Exception:
            pass
    return f"${total:,.0f} tracked across {len(entries)} entries"


def _wallet_brief():
    d = _read_json(_DATA / "wallet.json", {})
    if isinstance(d, dict):
        return f"Wallet ${d.get('balance', 0):.2f} / earned ${d.get('earned', 0):.2f}"
    return ""


def _toolkit_brief():
    """Physical/local capabilities JARVIS can actually perform right now."""
    lines = [
        "Desktop + OS: mouse/keyboard (pyautogui), screenshots, OCR, window control, "
        "apps, volume, brightness, wifi, bluetooth, power (sleep/shutdown/restart/lock), "
        "processes, clipboard, clipboard history, files, games, presentations",
        "Perception: screen capture + OCR (see/read/click on text you SEE), camera, "
        "voice (listen + speak), mood detection",
        "Web: browser automation, deep research, web search, scraping",
        "Comms: email, messages (whatsapp/instagram/telegram/discord), calls (via linked services)",
        "Money: build products, find jobs, apply on freelance platforms, deploy store, track earnings",
        "Brain: task planning, agent orchestration, self-heal, self-improvement",
    ]
    return "\n".join(lines)


def build_brief() -> str:
    try:
        parts = [
            "=== JARVIS'S CURRENT ASSETS ===",
            f"Accounts: {_accounts_brief()}",
            f"Products: {_products_brief()}",
            f"Earnings: {_earnings_brief()}",
        ]
        w = _wallet_brief()
        if w:
            parts.append(w)
        parts.append("")
        parts.append("=== JARVIS'S PHYSICAL TOOLKIT ===")
        parts.append(_toolkit_brief())
        return "\n".join(parts)
    except Exception as e:
        return f"=== INVENTORY ===\n(Inventory unavailable: {e})"


if __name__ == "__main__":
    print(build_brief())

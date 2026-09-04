"""
Strong Persistent Memory System for JARVIS.
Retains conversation history, user preferences, learned behaviors, facts.
Cross-session persistence with search and retrieval.
"""
import json
import time
import hashlib
from pathlib import Path
from threading import Lock
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

_CONVERSATIONS = _DATA_DIR / "conversations.json"
_PREFERENCES = _DATA_DIR / "preferences.json"
_FACTS = _DATA_DIR / "learned_facts.json"
_BEHAVIORS = _DATA_DIR / "behaviors.json"
_LOCK = Lock()

def _load_json(path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_json(path, data):
    with _LOCK:
        path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")

# ─── Conversation History ───────────────────────────────────────────

def log_conversation(user_msg: str, jarvis_reply: str, metadata: dict = None):
    """Store every user-JARVIS exchange with timestamp."""
    convos = _load_json(_CONVERSATIONS)
    if "exchanges" not in convos:
        convos["exchanges"] = []
    convos["exchanges"].append({
        "id": hashlib.md5(f"{time.time()}{user_msg}".encode()).hexdigest()[:12],
        "user": user_msg[:5000],
        "jarvis": jarvis_reply[:5000],
        "timestamp": datetime.now().isoformat(),
        "epoch": time.time(),
        "metadata": metadata or {},
    })
    # Keep last 500 exchanges
    convos["exchanges"] = convos["exchanges"][-500:]
    convos["total_exchanges"] = convos.get("total_exchanges", 0) + 1
    convos["last_updated"] = datetime.now().isoformat()
    _save_json(_CONVERSATIONS, convos)

def get_recent_conversations(n: int = 10) -> list:
    """Get last n conversation exchanges."""
    convos = _load_json(_CONVERSATIONS)
    exchanges = convos.get("exchanges", [])
    return exchanges[-n:]

def search_conversations(query: str, limit: int = 5) -> list:
    """Search conversation history for matching text."""
    convos = _load_json(_CONVERSATIONS)
    query_lower = query.lower()
    matches = []
    for ex in convos.get("exchanges", []):
        if query_lower in ex.get("user", "").lower() or query_lower in ex.get("jarvis", "").lower():
            matches.append(ex)
    return matches[-limit:]

def get_conversation_stats() -> dict:
    convos = _load_json(_CONVERSATIONS)
    exchanges = convos.get("exchanges", [])
    if not exchanges:
        return {"total": 0, "first": None, "last": None}
    return {
        "total": len(exchanges),
        "total_all_time": convos.get("total_exchanges", len(exchanges)),
        "first": exchanges[0].get("timestamp"),
        "last": exchanges[-1].get("timestamp"),
    }

# ─── User Preferences ──────────────────────────────────────────────

def set_preference(key: str, value: str, category: str = "general"):
    """Remember a user preference."""
    prefs = _load_json(_PREFERENCES)
    if category not in prefs:
        prefs[category] = {}
    prefs[category][key] = {
        "value": value,
        "updated": datetime.now().isoformat(),
    }
    _save_json(_PREFERENCES, prefs)

def get_preference(key: str, category: str = "general", default=None):
    """Recall a user preference."""
    prefs = _load_json(_PREFERENCES)
    return prefs.get(category, {}).get(key, {}).get("value", default)

def get_all_preferences() -> dict:
    return _load_json(_PREFERENCES)

def delete_preference(key: str, category: str = "general") -> bool:
    prefs = _load_json(_PREFERENCES)
    if category in prefs and key in prefs[category]:
        del prefs[category][key]
        _save_json(_PREFERENCES, prefs)
        return True
    return False

# ─── Learned Facts ─────────────────────────────────────────────────

def learn_fact(fact: str, source: str = "conversation", confidence: float = 1.0):
    """Store a learned fact about the world or user."""
    facts = _load_json(_FACTS)
    if "facts" not in facts:
        facts["facts"] = []
    fact_id = hashlib.md5(fact.encode()).hexdigest()[:10]
    # Avoid duplicates
    existing = [f for f in facts["facts"] if f.get("id") == fact_id]
    if existing:
        existing[0]["last_seen"] = datetime.now().isoformat()
        existing[0]["times_seen"] = existing[0].get("times_seen", 1) + 1
    else:
        facts["facts"].append({
            "id": fact_id,
            "fact": fact[:3000],
            "source": source,
            "confidence": confidence,
            "learned": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "times_seen": 1,
        })
    # Keep last 1000 facts
    facts["facts"] = sorted(facts["facts"], key=lambda x: x.get("last_seen", ""))[-1000:]
    facts["total_facts"] = len(facts["facts"])
    _save_json(_FACTS, facts)

def recall_facts(query: str = "", limit: int = 10) -> list:
    """Recall facts matching a query."""
    facts = _load_json(_FACTS)
    all_facts = facts.get("facts", [])
    if not query:
        return all_facts[-limit:]
    query_lower = query.lower()
    matches = [f for f in all_facts if query_lower in f.get("fact", "").lower()]
    return matches[-limit:]

def get_fact_stats() -> dict:
    facts = _load_json(_FACTS)
    return {"total_facts": facts.get("total_facts", 0)}

# ─── Learned Behaviors ─────────────────────────────────────────────

def learn_behavior(trigger: str, response: str, context: str = ""):
    """Learn a behavioral pattern: when user says X, do Y."""
    behaviors = _load_json(_BEHAVIORS)
    if "patterns" not in behaviors:
        behaviors["patterns"] = []
    behaviors["patterns"].append({
        "trigger": trigger[:500],
        "response": response[:500],
        "context": context[:500],
        "learned": datetime.now().isoformat(),
        "times_applied": 0,
    })
    behaviors["patterns"] = behaviors["patterns"][-200:]
    _save_json(_BEHAVIORS, behaviors)

def get_matching_behaviors(user_message: str) -> list:
    """Find behaviors that match the user's message."""
    behaviors = _load_json(_BEHAVIORS)
    msg_lower = user_message.lower()
    matches = []
    for p in behaviors.get("patterns", []):
        trigger = p.get("trigger", "").lower()
        if trigger and trigger in msg_lower:
            p["times_applied"] = p.get("times_applied", 0) + 1
            matches.append(p)
    if matches:
        _save_json(_BEHAVIORS, behaviors)
    return matches

# ─── Memory Summary for LLM Context ────────────────────────────────

def build_memory_context(max_chars: int = 4000) -> str:
    """Build a concise memory context string for the LLM system prompt."""
    parts = []
    
    # Recent conversations
    recent = get_recent_conversations(3)
    if recent:
        parts.append("Recent conversations:")
        for ex in recent[-2:]:
            parts.append(f"  User: {ex['user'][:100]}")
            parts.append(f"  JARVIS: {ex['jarvis'][:100]}")
    
    # Key preferences
    prefs = get_all_preferences()
    if prefs:
        pref_lines = []
        for cat, items in prefs.items():
            for k, v in list(items.items())[:3]:
                pref_lines.append(f"  {cat}.{k}: {str(v.get('value', ''))[:50]}")
        if pref_lines:
            parts.append("User preferences:")
            parts.extend(pref_lines[:5])
    
    # Recent facts
    facts = recall_facts("", limit=5)
    if facts:
        parts.append("Learned facts:")
        for f in facts:
            parts.append(f"  - {f['fact'][:80]}")
    
    context = "\n".join(parts)
    if len(context) > max_chars:
        context = context[:max_chars]
    return context

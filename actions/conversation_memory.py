"""Conversation Memory — remembers what was discussed, references it later."""
import json
import time
from pathlib import Path
from collections import deque
from typing import Optional

_MEM_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_MEM_DIR.mkdir(parents=True, exist_ok=True)
_CONV_MEMORY_PATH = _MEM_DIR / "conversation_memory.json"

class ConversationMemory:
    """
    Stores conversation summaries, key topics, user goals, and context.
    JARVIS uses this to remember what was discussed in previous sessions
    and reference it naturally in future conversations.
    """

    def __init__(self, max_sessions: int = 30, max_topics: int = 100):
        self._max_sessions = max_sessions
        self._max_topics = max_topics
        self._sessions: deque = deque(maxlen=max_sessions)
        self._topics: deque = deque(maxlen=max_topics)
        self._user_goals: list = []
        self._user_projects: list = []
        self._user_interests: list = []
        self._key_facts: list = []
        self._current_session_topics: list = []
        self._current_session_start = time.time()
        self._total_turns = 0
        self._load()

    def start_session(self):
        self._current_session_start = time.time()
        self._current_session_topics = []

    def record_turn(self, user_text: str, jarvis_text: str, mood: str = "neutral"):
        self._total_turns += 1
        topics = self._extract_topics(user_text)
        for t in topics:
            if t not in self._current_session_topics:
                self._current_session_topics.append(t)
            if not any(existing["topic"] == t for existing in self._topics):
                self._topics.append({
                    "topic": t,
                    "first_mentioned": time.time(),
                    "mention_count": 1,
                    "last_context": user_text[:200],
                })
            else:
                for existing in self._topics:
                    if existing["topic"] == t:
                        existing["mention_count"] += 1
                        existing["last_context"] = user_text[:200]
                        break

        goals = self._extract_goals(user_text)
        for g in goals:
            if g not in self._user_goals:
                self._user_goals.append(g)

        projects = self._extract_projects(user_text)
        for p in projects:
            if not any(existing["name"] == p for existing in self._user_projects):
                self._user_projects.append({
                    "name": p,
                    "first_mentioned": time.time(),
                    "status": "active",
                })

    def end_session(self, summary: str = ""):
        if self._total_turns == 0 and not self._current_session_topics:
            return
        duration = time.time() - self._current_session_start
        session = {
            "timestamp": self._current_session_start,
            "duration_seconds": duration,
            "topics": self._current_session_topics[:],
            "turns": self._total_turns,
            "summary": summary,
        }
        self._sessions.append(session)
        self._current_session_topics = []
        self._total_turns = 0
        self._save()

    def get_recent_context(self, num_sessions: int = 3) -> str:
        recent = list(self._sessions)[-num_sessions:]
        if not recent:
            return "No previous conversation history."
        lines = ["[CONVERSATION MEMORY]"]
        for s in recent:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(s["timestamp"]))
            topics_str = ", ".join(s["topics"][:5]) if s["topics"] else "general chat"
            lines.append(f"- {ts}: Talked about {topics_str} ({s['turns']} turns)")
            if s["summary"]:
                lines.append(f"  Summary: {s['summary']}")
        if self._user_goals:
            lines.append(f"\nUser goals: {', '.join(self._user_goals[:5])}")
        if self._user_projects:
            active = [p["name"] for p in self._user_projects if p["status"] == "active"]
            if active:
                lines.append(f"Active projects: {', '.join(active[:5])}")
        if self._key_facts:
            lines.append(f"Key facts: {', '.join(self._key_facts[:5])}")
        return "\n".join(lines)

    def get_hot_topics(self, top_n: int = 10) -> list:
        sorted_topics = sorted(self._topics, key=lambda x: x["mention_count"], reverse=True)
        return sorted_topics[:top_n]

    def get_user_context(self) -> dict:
        return {
            "goals": self._user_goals[:10],
            "projects": [p for p in self._user_projects if p["status"] == "active"][:10],
            "interests": self._user_interests[:10],
            "key_facts": self._key_facts[:10],
            "total_sessions": len(self._sessions),
            "total_topics": len(self._topics),
        }

    def add_key_fact(self, fact: str):
        if fact not in self._key_facts:
            self._key_facts.append(fact)
            self._save()

    def add_interest(self, interest: str):
        if interest not in self._user_interests:
            self._user_interests.append(interest)
            self._save()

    def _extract_topics(self, text: str) -> list:
        topics = []
        lower = text.lower()
        topic_keywords = {
            "coding": ["code", "coding", "program", "python", "javascript", "bug", "debug", "function", "class"],
            "crypto": ["crypto", "bitcoin", "btc", "eth", "ethereum", "trading", "portfolio", "coin"],
            "music": ["music", "song", "lyrics", "sing", "album", "artist", "playlist", "beat"],
            "school": ["school", "homework", "assignment", "exam", "class", "lecture", "professor", "grade"],
            "gaming": ["game", "gaming", "play", "fps", "rpg", "steam", "pc", "console"],
            "music_production": ["beat", "produce", "fl studio", "mix", "master", "sample", "loop"],
            "cybersecurity": ["hack", "pentest", "security", "vulnerability", "exploit", "scan"],
            "money": ["money", "earn", "income", "revenue", "profit", "freelance", "job"],
            "health": ["tired", "sleep", "energy", "stressed", "workout", "food", "water"],
            "social": ["friend", "girlfriend", "party", "hangout", "social", "instagram", "tiktok"],
        }
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in lower:
                    topics.append(topic)
                    break
        return topics

    def _extract_goals(self, text: str) -> list:
        goals = []
        lower = text.lower()
        goal_patterns = ["want to", "need to", "trying to", "goal", "plan to", "should", "gonna", "going to"]
        for pattern in goal_patterns:
            if pattern in lower:
                idx = lower.find(pattern)
                snippet = text[idx:idx+100].strip()
                if len(snippet) > 10:
                    goals.append(snippet[:100])
                    break
        return goals

    def _extract_projects(self, text: str) -> list:
        projects = []
        lower = text.lower()
        project_patterns = ["project", "app", "website", "bot", "tool", "script", "portfolio", "startup"]
        for pattern in project_patterns:
            if pattern in lower:
                idx = lower.find(pattern)
                start = max(0, idx - 30)
                snippet = text[start:idx+len(pattern)+30].strip()
                if len(snippet) > 5:
                    projects.append(snippet[:60])
                    break
        return projects

    def _save(self):
        try:
            data = {
                "sessions": list(self._sessions),
                "topics": list(self._topics),
                "user_goals": self._user_goals,
                "user_projects": self._user_projects,
                "user_interests": self._user_interests,
                "key_facts": self._key_facts,
            }
            _CONV_MEMORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            pass

    def _load(self):
        try:
            if _CONV_MEMORY_PATH.exists():
                data = json.loads(_CONV_MEMORY_PATH.read_text())
                for s in data.get("sessions", []):
                    self._sessions.append(s)
                for t in data.get("topics", []):
                    self._topics.append(t)
                self._user_goals = data.get("user_goals", [])
                self._user_projects = data.get("user_projects", [])
                self._user_interests = data.get("user_interests", [])
                self._key_facts = data.get("key_facts", [])
        except Exception:
            pass

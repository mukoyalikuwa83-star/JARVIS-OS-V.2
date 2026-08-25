"""Smart Screen Awareness — knows when to read screen, what to look at, understands context."""
import time
import hashlib
import json
import ctypes
import ctypes.wintypes as wt
from pathlib import Path
from collections import deque
from typing import Optional

_AWARENESS_PATH = Path(__file__).resolve().parent.parent / ".jarvis" / "screen_awareness.json"

class ScreenAwareness:
    """
    Tracks screen context over time so JARVIS knows:
    - What app is active and what the user is doing in it
    - When to proactively read the screen (app switch, error, idle, user reference)
    - What the user is referencing when they say "that", "this", "open that"
    - The user's current task flow (what they were doing, what they switched to)
    """

    def __init__(self, history_size: int = 50):
        self._history: deque = deque(maxlen=history_size)
        self._current_app = ""
        self._current_task = ""
        self._last_read_time = 0.0
        self._last_read_hash = ""
        self._app_switch_count = 0
        self._errors_detected: list = []
        self._user_workflows: list = []
        self._screen_changed = False
        self._pending_help = False
        self._help_topic = ""
        self._context_window: deque = deque(maxlen=10)
        self._load()

    def update(self, app_name: str, screen_hash: str, screen_text: str = ""):
        now = time.time()
        app_changed = app_name != self._current_app
        screen_changed = screen_hash != self._last_read_hash

        if app_changed:
            self._app_switch_count += 1
            if self._current_app:
                self._context_window.append({
                    "from": self._current_app,
                    "to": app_name,
                    "time": now,
                })

        self._current_app = app_name
        self._last_read_hash = screen_hash
        self._last_read_time = now
        self._screen_changed = screen_changed

        if screen_text:
            self._analyze_screen_content(app_name, screen_text, now)

        self._history.append({
            "app": app_name,
            "time": now,
            "changed": screen_changed,
            "task": self._current_task,
        })

        self._save()

    def _analyze_screen_content(self, app: str, text: str, now: float):
        lower = text.lower()

        error_words = ["error", "failed", "exception", "crash", "not responding", "timeout"]
        for word in error_words:
            if word in lower:
                self._errors_detected.append({
                    "app": app,
                    "error": word,
                    "time": now,
                    "context": text[:200],
                })
                self._pending_help = True
                self._help_topic = f"error in {app}: {word}"
                break

        if "login" in lower or "sign in" in lower or "password" in lower:
            self._pending_help = True
            self._help_topic = f"login screen in {app}"

        task_signals = {
            "coding": ["def ", "class ", "function", "import ", "const ", "let ", "var "],
            "research": ["google", "search", "wikipedia", "research", "find"],
            "communication": ["chat", "message", "email", "reply", "send"],
            "shopping": ["cart", "checkout", "buy", "price", "add to"],
            "gaming": ["health", "score", "level", "menu", "inventory"],
            "creative": ["design", "edit", "draw", "canvas", "layer", "brush"],
            "music": ["playlist", "track", "album", "artist", "play", "volume"],
        }
        for task, keywords in task_signals.items():
            for kw in keywords:
                if kw in lower:
                    self._current_task = task
                    break

    def should_read_screen(self) -> tuple[bool, str]:
        now = time.time()
        reasons = []

        if self._pending_help:
            self._pending_help = False
            return True, f"Detected issue: {self._help_topic}"

        if now - self._last_read_time > 60:
            reasons.append("been_60s")

        if self._app_switch_count > 0 and self._app_switch_count % 3 == 0:
            reasons.append("app_switches")

        if self._errors_detected and (now - self._errors_detected[-1]["time"]) < 10:
            reasons.append("recent_error")

        if reasons:
            return True, f"Screen awareness: {', '.join(reasons)}"

        return False, ""

    def get_current_context(self) -> str:
        if not self._current_app:
            return "No screen context available."
        lines = [f"Current app: {self._current_app}"]
        if self._current_task:
            lines.append(f"User appears to be: {self._current_task}")
        if self._context_window:
            recent = list(self._context_window)[-3:]
            flow = " → ".join(f"{c['from']}→{c['to']}" for c in recent)
            lines.append(f"Recent flow: {flow}")
        if self._errors_detected:
            last_err = self._errors_detected[-1]
            lines.append(f"Last error: {last_err['app']} - {last_err['error']}")
        return "\n".join(lines)

    def get_navigation_hint(self, user_text: str) -> str:
        lower = user_text.lower()
        hints = []

        if any(w in lower for w in ["that", "this", "it", "open that", "click that", "what's that"]):
            hints.append(f"The user is likely referring to something in {self._current_app}")
            if self._current_task:
                hints.append(f"They were {self._current_task}")

        if any(w in lower for w in ["go back", "switch back", "where was i"]):
            if self._context_window:
                last = list(self._context_window)[-1]
                hints.append(f"User probably wants to go back to {last['from']}")

        if any(w in lower for w in ["what am i doing", "what was i doing", "where am i"]):
            hints.append(f"User is in {self._current_app}, doing {self._current_task or 'something'}")

        return " | ".join(hints) if hints else ""

    def get_error_context(self) -> Optional[dict]:
        if self._errors_detected:
            return self._errors_detected[-1]
        return None

    def get_recent_apps(self, n: int = 5) -> list:
        seen = []
        for entry in reversed(self._history):
            if entry["app"] not in seen:
                seen.append(entry["app"])
            if len(seen) >= n:
                break
        return seen

    def _save(self):
        try:
            data = {
                "current_app": self._current_app,
                "current_task": self._current_task,
                "errors_detected": self._errors_detected[-20:],
                "context_window": list(self._context_window),
                "last_read_time": self._last_read_time,
            }
            _AWARENESS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _AWARENESS_PATH.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load(self):
        try:
            if _AWARENESS_PATH.exists():
                data = json.loads(_AWARENESS_PATH.read_text())
                self._current_task = data.get("current_task", "")
                self._errors_detected = data.get("errors_detected", [])
                for c in data.get("context_window", []):
                    self._context_window.append(c)
                self._last_read_time = 0
        except Exception:
            pass

    @staticmethod
    def get_active_window_title() -> str:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return "Unknown"
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            return title or "Unknown"
        except Exception:
            return "Unknown"

    def refresh(self) -> str:
        title = self.get_active_window_title()
        if title and title != "Unknown":
            app_changed = title != self._current_app
            if app_changed:
                self._app_switch_count += 1
                if self._current_app:
                    self._context_window.append({
                        "from": self._current_app,
                        "to": title,
                        "time": time.time(),
                    })
            self._current_app = title
            self._last_read_time = time.time()
        return self._current_app

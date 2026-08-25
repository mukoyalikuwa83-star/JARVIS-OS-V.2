"""Configurable assistant identity.

The assistant no longer has a forced fictional name or brand.  Its identity is
resolved from (in priority order):
  1. The ASSISTANT_NAME environment variable
  2. config/api_keys.json  -> "assistant_name"
  3. The default "Assistant"

The user's name is read from long-term memory (identity.name) when available.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
MEMORY_PATH = BASE_DIR / "memory" / "long_term.json"
DEFAULT_NAME = "Assistant"


def assistant_name() -> str:
    """Return the configured assistant name (never empty)."""
    env_name = os.environ.get("ASSISTANT_NAME", "").strip()
    if env_name:
        return env_name
    try:
        configured = str(
            json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("assistant_name", "") or ""
        ).strip()
    except Exception:
        configured = ""
    return configured or DEFAULT_NAME


def user_name() -> str | None:
    """Return the user's name from long-term memory, if stored."""
    try:
        memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        entry = (memory.get("identity") or {}).get("name")
    except Exception:
        return None
    if isinstance(entry, dict):
        value = entry.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    return None


def greeting() -> str:
    """Personalized greeting using the configured identity."""
    name = assistant_name()
    user = user_name()
    if user:
        return f"{name}. At your service, {user}. What would you like to accomplish today?"
    return f"{name}. At your service. What would you like to accomplish today?"

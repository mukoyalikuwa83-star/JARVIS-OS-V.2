"""Autonomy modes.

Controls how much confirmation the assistant requires before performing
sensitive operations.

  autonomous  — no confirmation gates; the assistant acts on the user's
                request immediately.
  balanced    — lightweight confirmation for destructive/sensitive actions
                (email send, message send, shutdown/restart).
  assisted    — confirmation for any action with side effects.

Resolved from, in priority order:
  1. The JARVIS_AUTONOMY environment variable
  2. config/api_keys.json  -> "autonomy"
  3. The default "balanced"
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

VALID_LEVELS = {"autonomous", "balanced", "assisted"}


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def autonomy_level() -> str:
    env_level = os.environ.get("JARVIS_AUTONOMY", "").strip().lower()
    if env_level in VALID_LEVELS:
        return env_level
    try:
        configured = str(
            json.loads((get_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")).get("autonomy", "") or ""
        ).strip().lower()
    except Exception:
        configured = ""
    if configured in VALID_LEVELS:
        return configured
    return "balanced"


def is_autonomous() -> bool:
    return autonomy_level() == "autonomous"


def requires_confirmation() -> bool:
    return autonomy_level() in {"balanced", "assisted"}

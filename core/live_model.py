"""Shared Gemini Live model selection for startup audio and the active assistant."""

from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
LIVE_ACTION = "bidiGenerateContent"

BLOCKED_MODELS = frozenset({
    "models/gemini-2.5-flash-live",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-3.1-flash-live-preview",
    "models/gemini-3.0-flash-live-preview",
    "models/gemini-2.5-flash-native-audio-latest",
    "models/gemini-2.5-flash-native-audio-preview-09-2025",
    "models/gemini-3.5-live-translate-preview",
    "models/gemini-2.5-flash-preview-tts",
})

KNOWN_WORKING_MODELS = frozenset({
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
})


def configured_live_model(config_path: Path) -> str:
    env_model = os.environ.get("GEMINI_LIVE_MODEL", "").strip()
    if env_model:
        return env_model
    try:
        configured = str(
            json.loads(config_path.read_text(encoding="utf-8")).get("live_model", "") or ""
        ).strip()
    except Exception:
        configured = ""
    return configured or DEFAULT_LIVE_MODEL


def _model_name(model) -> str:
    return str(getattr(model, "name", "") or "").strip()


def _model_actions(model) -> set[str]:
    actions = getattr(model, "supported_actions", None)
    if actions is None:
        actions = getattr(model, "supportedActions", None)
    return {str(action).lower() for action in (actions or [])}


def pick_live_model(client, config_path: Path) -> str:
    configured = configured_live_model(config_path)

    if configured in BLOCKED_MODELS:
        print(
            f"[Assistant] Configured model '{configured}' is blocklisted "
            f"(known broken). Using default: {DEFAULT_LIVE_MODEL}"
        )
        configured = DEFAULT_LIVE_MODEL

    try:
        models = list(client.models.list())
    except Exception as exc:
        print(
            f"[Assistant] Could not list Gemini models; using configured "
            f"live_model={configured}: {exc}"
        )
        return configured

    live_models = [
        _model_name(model)
        for model in models
        if (
            LIVE_ACTION.lower() in _model_actions(model)
            and _model_name(model)
            and _model_name(model) not in BLOCKED_MODELS
        )
    ]
    if not live_models:
        raise RuntimeError(
            "No Gemini Live-capable model is available for this API key. "
            "Check that Gemini Live API access is enabled."
        )

    if configured in live_models:
        return configured

    for model in KNOWN_WORKING_MODELS:
        if model in live_models:
            print(f"[Assistant] Auto-selected Live model: {model} (known working)")
            return model

    def score(name: str) -> tuple[int, str]:
        lowered = name.lower()
        if "native-audio" in lowered:
            return (0, name)
        if "live" in lowered and "flash" in lowered:
            return (1, name)
        if "flash-live" in lowered:
            return (2, name)
        if "flash" in lowered:
            return (3, name)
        return (4, name)

    selected = sorted(live_models, key=score)[0]
    print(f"[Assistant] Auto-selected Live model: {selected}")
    return selected


def get_fallback_model(client, current_model: str, config_path: Path) -> str | None:
    """Return the next-best model when current one keeps failing.
    
    Only returns models we KNOW work with native audio — never random API models.
    """
    for model in KNOWN_WORKING_MODELS:
        if model != current_model and model not in BLOCKED_MODELS:
            return model
    return None

"""Self-healing error reporter: logs errors, diagnoses root causes, auto-fixes config."""

import json
import time
from pathlib import Path
from datetime import datetime

_ERROR_LOG = Path(__file__).resolve().parent.parent / ".jarvis" / "error_history.json"
_FIX_LOG = Path(__file__).resolve().parent.parent / ".jarvis" / "auto_fixes.json"

_ERROR_PATTERNS = {
    "content_type_audio": {
        "cause": "Model rejected AUDIO response modality or speech_config",
        "fix": "remove_speech_config",
        "description": "Removed speech_config and output_audio_transcription from config",
    },
    "response_modalities": {
        "cause": "Model rejected explicit response_modalities setting",
        "fix": "remove_response_modalities",
        "description": "Removed response_modalities from config entirely",
    },
    "voice": {
        "cause": "Voice not supported for this model",
        "fix": "fallback_voice",
        "description": "Fell back to default voice",
    },
    "session_duration_limit": {
        "cause": "Session expired after max duration",
        "fix": "reconnect_instantly",
        "description": "Reconnected immediately (expected)",
    },
    "1006": {
        "cause": "WebSocket abnormal closure (keepalive timeout)",
        "fix": "reconnect_with_backoff",
        "description": "Reconnected with exponential backoff",
    },
    "1007": {
        "cause": "WebSocket invalid data (protocol error)",
        "fix": "reconnect_with_backoff",
        "description": "Reconnected with exponential backoff",
    },
    "1011": {
        "cause": "Server error (internal failure)",
        "fix": "reconnect_with_backoff",
        "description": "Reconnected with exponential backoff",
    },
    "api_key": {
        "cause": "Invalid or missing API key",
        "fix": "check_env",
        "description": "Check .env file for GEMINI_API_KEY",
    },
    "quota": {
        "cause": "API quota exceeded",
        "fix": "wait_and_retry",
        "description": "Waited and retried",
    },
    "timed out": {
        "cause": "Connection timed out — server unreachable or network issue",
        "fix": "retry",
        "description": "Network timeout. Retrying with backoff.",
    },
    "opening handshake": {
        "cause": "WebSocket handshake failed — network/DNS issue",
        "fix": "retry",
        "description": "WebSocket connection failed during handshake. Retrying.",
    },
    "connection refused": {
        "cause": "Server refused connection",
        "fix": "retry",
        "description": "Server unreachable. Retrying with backoff.",
    },
}


def _load_history():
    try:
        return json.loads(_ERROR_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_history(history):
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        _ERROR_LOG.write_text(json.dumps(history[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _load_fixes():
    try:
        return json.loads(_FIX_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_fixes(fixes):
    try:
        _FIX_LOG.parent.mkdir(parents=True, exist_ok=True)
        _FIX_LOG.write_text(json.dumps(fixes[-50:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def diagnose_error(error_msg: str) -> dict:
    """Diagnose an error and return the best fix."""
    msg_lower = str(error_msg).lower()
    for pattern, info in _ERROR_PATTERNS.items():
        if pattern in msg_lower:
            return {
                "pattern": pattern,
                "cause": info["cause"],
                "fix": info["fix"],
                "description": info["description"],
                "confidence": "high",
            }
    if "timed out" in msg_lower or "timeout" in msg_lower:
        return {
            "pattern": "timeout",
            "cause": f"Connection timed out: {error_msg[:200]}",
            "fix": "retry",
            "description": "Network timeout — server unreachable or slow. Will retry.",
            "confidence": "high",
        }
    if "opening handshake" in msg_lower:
        return {
            "pattern": "opening_handshake",
            "cause": f"WebSocket handshake failed: {error_msg[:200]}",
            "fix": "retry",
            "description": "WebSocket handshake failed — usually network/DNS issue.",
            "confidence": "high",
        }
    return {
        "pattern": "unknown",
        "cause": f"Unrecognized error: {error_msg[:200]}",
        "fix": "retry",
        "description": "Unknown error — retrying connection",
        "confidence": "low",
    }


def report_error(error_msg: str, model: str = "", config_summary: str = "") -> dict:
    """Log an error and return diagnosis."""
    diagnosis = diagnose_error(error_msg)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "error": str(error_msg)[:500],
        "model": model,
        "config": config_summary,
        "diagnosis": diagnosis,
    }
    history = _load_history()
    history.append(entry)
    _save_history(history)
    return diagnosis


def report_fix(diagnosis: dict, success: bool):
    """Log an auto-fix attempt."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "fix": diagnosis.get("fix", "unknown"),
        "description": diagnosis.get("description", ""),
        "success": success,
    }
    fixes = _load_fixes()
    fixes.append(entry)
    _save_fixes(fixes)


def get_error_summary() -> str:
    """Get a human-readable summary of recent errors."""
    history = _load_history()
    if not history:
        return "No errors recorded."
    recent = history[-10:]
    lines = [f"Last {len(recent)} errors:"]
    for e in recent:
        diag = e.get("diagnosis", {})
        lines.append(f"  [{e.get('timestamp', '?')}] {diag.get('cause', e.get('error', '?')[:100])}")
    return "\n".join(lines)


def should_change_model(error_count: int) -> bool:
    """If same error happens 3+ times, suggest changing model."""
    return error_count >= 3

import asyncio
import os
import re
import threading
import json
from core.error_healer import report_error, report_fix, should_change_model
import sys
import warnings
import traceback
import atexit
from pathlib import Path

os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font=false")
os.environ.setdefault("QT_MESSAGE_PATTERN", "%{message}")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sounddevice")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="openai")
warnings.filterwarnings("ignore", message=".*Setting the shape on a NumPy array.*")
warnings.filterwarnings("ignore", message=".*numpy array.*")
warnings.filterwarnings("ignore", message=".*numpy.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Py玤back.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

_original_showwarning = warnings.showwarning
def _silence_sounddevice_warnings(msg, *args, **kwargs):
    if "sounddevice" in str(msg) or "numpy" in str(msg).lower():
        return
    _original_showwarning(msg, *args, **kwargs)
warnings.showwarning = _silence_sounddevice_warnings

_audio_streams = []

def _cleanup_audio():
    for stream in _audio_streams:
        try:
            stream.stop()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass
    _audio_streams.clear()

atexit.register(_cleanup_audio)

# sounddevice deferred to JarvisLive.__init__ for faster startup
sd = None

# Handle pydantic version conflicts gracefully
try:
    from google import genai
    from google.genai import types
except ImportError as _import_err:
    if "WrapValidator" in str(_import_err) or "pydantic" in str(_import_err):
        try:
            import subprocess, sys as _sys
            _sys.stdout.write("Fixing pydantic version...\n")
            subprocess.run([_sys.executable, "-m", "pip", "install", "--force-reinstall", "pydantic==2.13.5", "--index-url", "https://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com", "--quiet"], capture_output=True, timeout=120)
            from google import genai
            from google.genai import types
        except Exception:
            genai = None
            types = None
    else:
        genai = None
        types = None

def _qt_message_handler(mode, context, message):
    if "font" in message.lower() or "opentype" in message.lower():
        return
    if "dpiawareness" in message.lower():
        return
    if mode == 0:  # QtDebugMsg
        return
    sys.stderr.write(message + "\n")
    sys.stderr.flush()

try:
    from PyQt6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(_qt_message_handler)
except ImportError:
    pass

def _global_exception_hook(exc_type, exc_value, exc_tb):
    """Catch any unhandled exception that would silently kill the process."""
    import traceback as _tb
    _tb.print_exception(exc_type, exc_value, exc_tb)
    sys.stderr.flush()
sys.excepthook = _global_exception_hook

import signal as _signal
def _signal_handler(signum, frame):
    print(f"\n[SIGNAL] Received signal {signum}, shutting down...")
    sys.exit(0)
for _sig in (_signal.SIGTERM, _signal.SIGINT):
    try:
        _signal.signal(_sig, _signal_handler)
    except (OSError, ValueError):
        pass

def _async_exception_hook(loop, context):
    """Catch unhandled async exceptions that would silently kill the event loop."""
    import traceback as _tb
    exc = context.get("exception")
    if exc:
        _tb.print_exception(type(exc), exc, exc.__traceback__)
    else:
        print(f"[AsyncError] {context.get('message', 'unknown')}")
    sys.stderr.flush()
try:
    asyncio.get_event_loop()
except RuntimeError:
    pass

try:
    from ui import JarvisUI
except Exception as e:
    print(f"[FATAL] ui import failed: {e}")
    raise

try:
    from api import status as jarvis_status
except Exception:
    jarvis_status = None

try:
    from memory.memory_manager import (
        load_memory, update_memory, format_memory_for_prompt,
    )
except Exception:
    load_memory = lambda: {}
    update_memory = lambda *a, **k: None
    format_memory_for_prompt = lambda *a: ""

import hashlib
import time

# ─── Lazy Action Loader (replaces 99 imports) ───────────────────────────
try:
    from actions.lazy_loader import get_handler as _lazy, preload_handlers as _preload
except Exception:
    _lazy = lambda name: None
    _preload = lambda *a: None

# Preload critical handlers used at startup
_preload(
    "mood_detector", "conversation_memory", "tts_engine", "screen_awareness",
    "real_hustle", "autonomous_worker", "money_makers", "gumroad_api",
    "stripe_payments", "screen_automation", "notification_push",
)

# ─── Core Module Imports (keep essential) ───────────────────────────────
try:
    from core.live_model import pick_live_model, get_fallback_model
except Exception:
    pick_live_model = None
    get_fallback_model = None

try:
    from core.identity import assistant_name, greeting as build_greeting
except Exception:
    assistant_name = "JARVIS"
    build_greeting = lambda *a, **k: "Hello."

try:
    from core import qa_mode
except Exception:
    class _QAMode:
        qa_enabled = staticmethod(lambda: False)
        guard_tool_call = staticmethod(lambda *a: None)
        qa_block_message = staticmethod(lambda *a: "")
    qa_mode = _QAMode()

try:
    from awareness.engine import AwarenessEngine
except Exception:
    AwarenessEngine = None

try:
    from memory.answer_cache import get_cached_answer, save_cached_answer
except Exception:
    get_cached_answer = lambda *a: None
    save_cached_answer = lambda *a, **k: None

# ─── Core Classes (lazy) ───────────────────────────────────────────────
try:
    from core.gemini_compat import GeminiCompat
except Exception:
    GeminiCompat = None

try:
    from core.autonomy import Autonomy
except Exception:
    Autonomy = None

try:
    from core.api_key_validator import ApiKeyValidator
except Exception:
    ApiKeyValidator = None

try:
    from memory.task_history import TaskHistory
except Exception:
    TaskHistory = None

try:
    from memory.config_manager import ConfigManager
except Exception:
    ConfigManager = None

try:
    from agent.executor import AgentExecutor
except Exception:
    AgentExecutor = None

try:
    from agent.error_handler import AgentErrorHandler
except Exception:
    AgentErrorHandler = None

try:
    from agent.planner import AgentPlanner
except Exception:
    AgentPlanner = None

# ─── Environment ───────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _load_dotenv():
    """Load .env file if it exists. Silently skip if not found."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except Exception:
        pass


BASE_DIR = get_base_dir()
_load_dotenv()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 48000
SUPPORTED_VOICE_NAMES = {
    "puck", "charon", "kore", "fenrir", "aoede",
    "leda", "orus", "schedar", "zubenelgenubi"
}
DEFAULT_VOICE_NAME   = "puck"

RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024
STARTUP_CLAPS_REQUIRED = 2
STARTUP_CLAP_MAX_GAP_SECONDS = 4.0
STARTUP_CLAP_COOLDOWN_SECONDS = 0.22
SELF_QUIT_GOODBYE = (
    "Certainly. It has been a privilege. I am going offline now. "
    "Until next time."
)

LIVE_VAD_SILENCE_MS = 80
_LIVE_RECONNECT_MAX_DELAY = 5.0
_LIVE_KEEPALIVE_INTERVAL = 15.0
_MIC_GAIN_DB = 95
_MIC_NOISE_GATE_THRESHOLD = 0.5
_MIC_AGC_TARGET = 18000
_MIC_AGC_RATE = 0.25
_MIC_DEVICE_ID = int(os.environ.get("JARVIS_MIC_DEVICE", "5"))  # Microphone device ID; override with JARVIS_MIC_DEVICE env var

# Tool calls that mutate external state, the UI, or running processes. They are
# executed strictly in order so later calls always see the effects of earlier ones.
_MUTATING_TOOL_NAMES = frozenset({
    "send_message", "prepare_message_reply", "check_messages", "email_control",
    "file_controller", "file_processor", "reminder", "game_updater",
    "computer_settings", "computer_control", "desktop_control", "media_control",
    "save_memory", "jarvis_ui_control", "screen_process", "code_helper", "dev_agent",
    "agent_task", "task_status", "create_presentation", "deep_research",
    "bluetooth_control", "wifi_control", "calendar_control", "autonomous_control",
    "market_monitor", "daily_briefing", "contact_manager", "taskbar_detect", "full_control",
    "autonomous_brain", "money_makers", "self_evolution", "auto_start", "autonomous_worker",
    "gumroad_api", "social_media", "content_engine",
})

_SELF_QUIT_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"\b(?:quit|close|exit|shut\s+down|turn\s+off|power\s+down|go\s+offline)\s+(?:yourself|the\s+assistant)\b",
    r"\b(?:quit|close|exit|shut\s+down|turn\s+off|power\s+down)\s+(?:down|off)\s+(?:yourself|the\s+assistant)\b",
    r"\b(?:go|take\s+yourself)\s+offline\b",
    r"\b(?:shut|power|turn)\s+(?:yourself|the\s+assistant)\s+(?:down|off)\b",
    r"\b(?:please\s+)?shut\s+down\s+(?:for\s+the\s+day|now)\b",
))


def _unwrap_exception_groups(exc):
    """Yield every leaf exception, recursing through ExceptionGroup wrappers."""
    stack = [exc]
    while stack:
        current = stack.pop()
        if isinstance(current, BaseExceptionGroup):
            stack.extend(current.exceptions)
        else:
            yield current


def _brief_error(exc) -> str:
    """Return a short error summary for logging."""
    msg = str(exc).splitlines()[0][:120]
    return f"{type(exc).__name__}: {msg}" if msg else type(exc).__name__


def _is_normal_live_close_error(exc) -> bool:
    """Recognize a clean websocket close (1000 OK), including inside a task group."""
    for item in _unwrap_exception_groups(exc):
        if type(item).__name__ == "ConnectionClosedOK":
            return True
        message = str(item).lower()
        if "sent 1000 (ok); then received 1000 (ok)" in message:
            return True
        if "connection closed ok" in message or "websocket 1000" in message:
            return True
    return False


def _is_transient_live_connection_error(exc) -> bool:
    """Recognize retryable network failures, including inside a task group."""
    for item in _unwrap_exception_groups(exc):
        if isinstance(item, (ConnectionError, TimeoutError)):
            return True
        if "ConnectionClosed" in type(item).__name__:
            return True
        if isinstance(item, OSError) and item.errno in (104, 54):
            return True
        if genai is not None and isinstance(item, genai.errors.APIError):
            msg = str(item)
            if "1006" in msg or "1007" in msg or "1011" in msg or "1012" in msg or "1014" in msg:
                return True
        message = str(item).lower()
        if "connection reset" in message or "connection aborted" in message:
            return True
        if "connection refused" in message:
            return True
        if "internal error" in message:
            return True
        if "invalid argument" in message or "invalid frame" in message:
            return True
        if "received 1006" in message or "received 1007" in message:
            return True
        if "keepalive" in message and "timeout" in message:
            return True
        if "timed out" in message or "opening handshake" in message:
            return True
    return False


def _live_response_audio_bytes(response) -> bytes:
    """Extract audio from server_content parts without the SDK data shortcut."""
    try:
        server_content = response.server_content
    except Exception:
        return b""
    if server_content is None:
        return b""
    model_turn = getattr(server_content, "model_turn", None)
    if model_turn is None:
        return b""
    for part in getattr(model_turn, "parts", None) or []:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue
        mime = str(getattr(inline, "mime_type", "") or "")
        if mime.startswith("audio/"):
            return getattr(inline, "data", b"") or b""
    return b""


def _live_reconnect_delay(attempt: int) -> float:
    """Exponential backoff with jitter, capped at sane maximum."""
    import random
    base = 0.5 * (2.0 ** (max(1, int(attempt)) - 1))
    jitter = random.uniform(0.8, 1.2)
    return min(_LIVE_RECONNECT_MAX_DELAY, base * jitter)


def wait_for_startup_claps(
    required: int = STARTUP_CLAPS_REQUIRED,
    *,
    timeout: float | None = None,
    stream_factory=None,
) -> bool:
    """Optional clap-powered startup ritual.

    Not required by default. Only engaged when JARVIS_REQUIRE_CLAP_GATE=1
    (or JARVIS_ENABLE_CLAP_GATE=1 for an opt-in ritual). Normal launches start
    immediately without listening for claps.
    """
    explicit = os.environ.get("JARVIS_REQUIRE_CLAP_GATE", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        pass
    else:
        return True
    if os.environ.get("JARVIS_SKIP_CLAP_GATE", "").strip().lower() in {"1", "true", "yes", "on"}:
        print("[Assistant] 👏 Startup clap gate bypassed (JARVIS_SKIP_CLAP_GATE).")
        return True
    # Some macOS/AUHAL configurations expose a nominal input device but reject
    # every PortAudio operation (PaErrorCode -9986). Avoid repeatedly starting
    # a failing Core Audio stream; users with a working mic can opt in.
    if sys.platform == "darwin" and stream_factory is None and os.environ.get("JARVIS_ENABLE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("[Assistant] ⚠️ macOS microphone gate disabled for this audio configuration.")
        print("[Assistant] Continuing without clap startup. Set JARVIS_ENABLE_CLAP_GATE=1 to force it.")
        return True

    required = max(1, int(required))
    global sd
    if sd is None:
        try:
            import sounddevice as sd
        except Exception:
            pass
    stream_factory = stream_factory or (sd.InputStream if sd is not None else None)
    try:
        import numpy as np
    except ImportError:
        print("[Assistant] ❌ Startup clap gate needs numpy. Set JARVIS_SKIP_CLAP_GATE=1 to bypass.")
        return False

    clap_times: list[float] = []
    last_clap_at = 0.0
    # Microphone input levels vary considerably between Mac models.  The old
    # fixed 0.12 RMS / 0.32 peak gates rejected quiet real claps, while laptop
    # fan noise could sometimes trip them.  Track the room floor and use both
    # transient shape (crest factor) and energy to identify a clap.
    noise_floor = 0.008
    finished = threading.Event()
    started_at = time.monotonic()

    def callback(indata, frames, time_info, status):
        nonlocal last_clap_at, noise_floor, clap_times
        if status:
            print(f"[Assistant] ⚠️ Clap mic: {status}")
        samples = np.asarray(indata, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            return
        magnitude = np.abs(samples)
        rms = float(np.sqrt(np.mean(samples * samples)))
        peak = float(np.max(magnitude))
        # Only let low-energy frames teach the noise floor; otherwise a clap
        # would raise the threshold immediately and make the second clap hard
        # to detect.
        if rms < max(0.08, noise_floor * 6.0):
            noise_floor = (noise_floor * 0.96) + (rms * 0.04)
        threshold = max(0.100, noise_floor * 6.5)
        peak_threshold = max(0.35, noise_floor * 15.0)
        crest_factor = peak / max(rms, 1e-6)
        now = time.monotonic()
        # A valid clap must be either a sharp transient with meaningful energy
        # or a genuinely loud impact. This rejects speech, fan noise, and most
        # desk/keyboard taps that only have a brief peak.
        is_transient = crest_factor >= 2.20 and rms >= threshold
        is_loud = rms >= max(0.28, noise_floor * 15.0)
        if (
            peak < peak_threshold
            or not (is_transient or is_loud)
            or now - last_clap_at < STARTUP_CLAP_COOLDOWN_SECONDS
        ):
            return
        if clap_times and now - clap_times[-1] > STARTUP_CLAP_MAX_GAP_SECONDS:
            clap_times = []
        clap_times.append(now)
        last_clap_at = now
        print(f"[Assistant] 👏 Clap {len(clap_times)}/{required} detected")
        if len(clap_times) >= required:
            finished.set()

    print(f"[Assistant] 👏 Waiting for {required} claps to power up...")
    # PortAudio on macOS commonly rejects 16 kHz even when the microphone is
    # available (PaErrorCode -9986). Prefer the device's native rate, then
    # retry standard rates before reporting that the microphone is unavailable.
    sample_rates = [SEND_SAMPLE_RATE, 44100, 48000]
    input_device = None
    try:
        if stream_factory is sd.InputStream:
            try:
                default_device = sd.default.device
                try:
                    input_index = int(default_device[0])
                except (TypeError, IndexError, ValueError):
                    input_index = -1
                if input_index < 0:
                    print("[Assistant] ⚠️ macOS reports no default microphone device.")
                    if os.environ.get("JARVIS_REQUIRE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
                        print("[Assistant] ⚠️ Continuing without the clap gate; microphone input is unavailable.")
                        return True
                    raise RuntimeError("no default microphone device")
                input_device = input_index
                device = sd.query_devices(input_device if input_device is not None else None, "input")
                if int(device.get("max_input_channels", 0)) < 1:
                    raise RuntimeError("no input channels are available")
                native_rate = int(float(device.get("default_samplerate", 0)))
                if native_rate > 0:
                    sample_rates.insert(0, native_rate)
            except Exception:
                pass
        sample_rates = list(dict.fromkeys(sample_rates))
        last_error = None
        for sample_rate in sample_rates:
            try:
                if stream_factory is sd.InputStream:
                    # Validate the format before constructing a live AUHAL
                    # stream; macOS can report a device but reject it with
                    # PaErrorCode -9986 during stream startup.
                    sd.check_input_settings(
                        device=input_device,
                        samplerate=sample_rate,
                        channels=CHANNELS,
                        dtype="float32",
                    )
                with stream_factory(
                    samplerate=sample_rate,
                    device=input_device,
                    channels=CHANNELS,
                    dtype="float32",
                    blocksize=0,
                    latency="high",
                    callback=callback,
                ):
                    while not finished.wait(0.05):
                        if timeout is not None and time.monotonic() - started_at >= timeout:
                            print("[Assistant] ⏱️ Startup clap gate timed out.")
                            return False
                break
            except Exception as exc:
                last_error = exc
                if finished.is_set():
                    break
        else:
            raise last_error or RuntimeError("no compatible microphone sample rate")
    except KeyboardInterrupt:
        print("\n[Assistant] Startup cancelled.")
        return False
    except Exception as exc:
        print(f"[Assistant] ❌ Startup clap microphone unavailable: {exc}")
        if os.environ.get("JARVIS_REQUIRE_CLAP_GATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
            print("[Assistant] ⚠️ Continuing without the clap gate; microphone input is unavailable.")
            print("[Assistant] Restore microphone access to use voice input.")
            return True
        print("[Assistant] Clap gate required. Set JARVIS_SKIP_CLAP_GATE=1 to bypass it.")
        return False

    print("[Assistant] ⚡ Two claps detected. Powering up...")
    return True

def _get_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please set it to your Gemini API key.")
    return api_key


def _normalize_voice_name(voice_name: str | None) -> str:
    if not voice_name:
        return DEFAULT_VOICE_NAME
    candidate = voice_name.strip().lower()
    return candidate if candidate in SUPPORTED_VOICE_NAMES else DEFAULT_VOICE_NAME


def _is_unsupported_voice_error(exc: Exception) -> bool:
    if genai is None or not isinstance(exc, genai.errors.APIError):
        return False
    code = getattr(exc, "code", None)
    msg = str(exc).lower()
    if code == 1007:
        return "requested voice api_name" in msg and "not available for model" in msg
    return "requested voice api_name" in msg and "not available for model" in msg


def _load_voice_name() -> str:
    voice = os.environ.get("GEMINI_VOICE_NAME")
    if voice:
        return _normalize_voice_name(voice)
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return _normalize_voice_name(json.load(f).get("voice_name"))
    except Exception:
        return DEFAULT_VOICE_NAME


def _load_system_prompt() -> str:
    name = assistant_name()
    user = load_memory().get("identity", {}).get("name")
    user_value = None
    if isinstance(user, dict):
        user_value = user.get("value")
    elif isinstance(user, str):
        user_value = user
    identity_line = (
        f"You are {name}, the user's personal AI assistant."
        + (f" The user's name is {user_value}." if user_value else "")
        + " Address the user naturally, without honorifics."
    )
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        inventory = ""
        try:
            from core.inventory import build_brief
            inventory = "\n\n" + build_brief()
        except Exception:
            pass
        return (
            identity_line
            + "\n\n"
            + prompt
            + inventory
        )
    except Exception:
        return (
            f"{identity_line} "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

from core.tool_registry import TOOL_DECLARATIONS

class JarvisLive:

    def __init__(self, ui: JarvisUI, voice_name: str = "Puck"):
        global sd
        if sd is None:
            import sounddevice as sd
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.voice_name     = voice_name
        self.ui.on_text_command = self._on_text_command
        self._voice_changed  = threading.Event()
        self._turn_done_event: asyncio.Event | None = None
        self._tts_engine = None
        self._ext_tts_provider = ""
        self._ext_tts_voice_id = ""
        self._ext_tts_api_key = ""
        self._current_input_transcript = ""
        self._last_input_transcript = ""
        self._last_input_transcript_at = 0.0
        self._pending_self_quit = False
        self._pending_self_quit_farewell_received = False
        self._self_quit_timer = None
        self._shutdown_requested = threading.Event()
        self._tour_active = False
        self._reconnect_attempt = 0
        self._last_keepalive_activity = 0.0
        self._last_screen_snapshot = b""
        self._last_screen_mime = "image/png"
        self._last_vision_time = 0.0
        self._last_net_bytes = (0, 0)
        self._first_greet_done = False
        self._genai_client = None
        self._prev_screen_hash = ""
        self._last_screen_change_time = 0.0
        self._barge_in_event = threading.Event()
        self._last_barge_in_time = 0.0
        self._playback_started_at = 0.0
        self._barge_in_grace_ms = 0.5
        self._playback_energy = 0.0
        self._mic_energy_level = 0.0
        self._mic_energy_lock = threading.Lock()
        self._send_lock = None
        self._last_user_speech_at = 0.0
        self._user_is_addressing_jarvis = False
        self._conversation_turn_count = 0
        self._last_tool_call_time = 0.0
        self._consecutive_silence = 0
        self._mood_analyzer = _lazy("mood_detector")()
        self._screen_awareness = _lazy("screen_awareness")()
        self._awareness_engine = AwarenessEngine(
            popup_scheduler=lambda msg, ptype=None: None
        )
        try:
            self._awareness_engine.start()
        except Exception:
            pass
        self._hustle_engine = _lazy("real_hustle")()
        self._conv_memory = _lazy("conversation_memory")()

    async def _safe_task(self, name: str, coro):
        """Wrap a coroutine so a single task crash never kills the TaskGroup."""
        try:
            return await coro
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"[Task:{name}] ❌ crashed: {e}")
            try:
                self.ui.write_log(f"ERR: Task {name} crashed: {str(e)[:60]}")
            except Exception:
                pass

    _WAKE_WORDS = (
        "jarvis", "hey jarvis", "ok jarvis", "yo jarvis",
        "j-a-r-v-i-s", "jarvis,", "jarvis.",
    )

    def _check_wake_word(self, text: str) -> bool:
        lower = text.lower().strip()
        for w in self._WAKE_WORDS:
            if lower.startswith(w) or f" {w} " in lower:
                return True
        return False

    def _detect_barge_in_context(self, transcript: str) -> str:
        if not transcript:
            return "silence"
        lower = transcript.lower()
        if self._check_wake_word(lower):
            self._user_is_addressing_jarvis = True
            return "direct_address"
        if self._is_speaking:
            with self._mic_energy_lock:
                mic_level = self._mic_energy_level
            if mic_level > 400 / 32768.0:
                self._user_is_addressing_jarvis = True
                return "barge_in"
        time_since_speech = time.monotonic() - self._last_user_speech_at if self._last_user_speech_at else 999
        if time_since_speech < 3.0:
            return "follow_up"
        self._user_is_addressing_jarvis = False
        return "ambient"

    def get_mood_status(self) -> dict:
        return {
            "mood": self._mood_analyzer.get_mood(),
            "confidence": self._mood_analyzer.get_confidence(),
            "energy": self._mood_analyzer.get_energy(),
            "stress": self._mood_analyzer.get_stress(),
            "fatigue": self._mood_analyzer.get_fatigue(),
            "adaptation": self._mood_analyzer.get_adaptation_hint(),
            "turns": self._conversation_turn_count,
            "addressing_jarvis": self._user_is_addressing_jarvis,
        }

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        self._current_input_transcript = str(text or "").strip()
        self._last_input_transcript = self._current_input_transcript
        self._last_input_transcript_at = time.monotonic()
        outgoing_text = text
        if (
            not getattr(self, "_pending_self_quit", False)
            and self._is_explicit_self_quit_transcript(self._current_input_transcript)
        ):
            self._queue_self_quit_after_farewell()
            outgoing_text = (
                "[VERIFIED LOCAL SELF-SHUTDOWN] The user explicitly asked the assistant to quit. "
                f'Say exactly: "{SELF_QUIT_GOODBYE}" Do not call a tool and say nothing else.'
            )
        self._safe_send_content_sync(
            turns={"parts": [{"text": outgoing_text}]},
            turn_complete=True
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
            self.ui.set_mic_state("speaking")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")
            self.ui.set_mic_state("listening")

    def speak(self, text: str) -> bool:
        if not self._loop or not self.session:
            return False
        try:
            self._safe_send_content_sync(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            )
            return True
        except Exception:
            return False

    def _speak_vision_result(self, text: str) -> bool:
        """Send finished vision text through the assistant's active voice session."""
        result = " ".join(str(text or "").split())
        if not result:
            return False
        directive = (
            "[INTERNAL VISION OUTPUT] Read the following vision result to the user "
            "verbatim. Do not add an introduction, commentary, or a tool call. "
            f"Vision result: {json.dumps(result, ensure_ascii=False)}"
        )
        return self.speak(directive)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"{tool_name} encountered an error. {short}")

    @staticmethod
    def _is_explicit_self_quit_transcript(text: str) -> bool:
        """Only match commands that clearly target the assistant, never the computer."""
        normalized = " ".join(str(text or "").lower().split())
        if not normalized:
            return False
        if re.search(r"\b(?:computer|mac|pc|system|machine)\b", normalized):
            return False
        if re.search(r"\b(?:stop talking|be quiet|cancel|never mind)\b", normalized):
            return False
        if normalized in {
            "quit", "exit", "shutdown", "shut down", "turn off", "power down",
            "go offline", "goodbye assistant",
        }:
            return True
        return any(pattern.search(normalized) for pattern in _SELF_QUIT_PATTERNS)

    def _queue_self_quit_after_farewell(self) -> None:
        """Arm shutdown without closing until the response audio is fully drained."""
        self._pending_self_quit = True
        self._pending_self_quit_farewell_received = False
        try:
            self.ui.write_log("SYS: Shutdown queued; waiting for the farewell.")
        except Exception:
            pass
        # A voice model can occasionally omit audio/turn_complete. Do not
        # leave the user with a permanently armed shutdown in that case.
        try:
            if self._self_quit_timer is not None:
                self._self_quit_timer.cancel()
            self._self_quit_timer = threading.Timer(8.0, self._force_complete_self_quit)
            self._self_quit_timer.daemon = True
            self._self_quit_timer.start()
        except Exception as e:
            print(f"[Assistant] ⚠️ Self-quit timer failed: {e}", flush=True)

    def _force_complete_self_quit(self) -> None:
        if not getattr(self, "_pending_self_quit", False):
            return
        self._pending_self_quit_farewell_received = True
        self._complete_self_quit_after_audio()

    def _mark_self_quit_farewell_received(self) -> None:
        if getattr(self, "_pending_self_quit", False):
            self._pending_self_quit_farewell_received = True

    def _complete_self_quit_after_audio(self) -> bool:
        """Close through the UI only after a farewell turn has actually completed."""
        if not (
            getattr(self, "_pending_self_quit", False)
            and getattr(self, "_pending_self_quit_farewell_received", False)
        ):
            return False
        self._pending_self_quit = False
        self._pending_self_quit_farewell_received = False
        if getattr(self, "_self_quit_timer", None) is not None:
            self._self_quit_timer.cancel()
            self._self_quit_timer = None
        self.request_shutdown()
        self.ui.handle_ui_command("quit")
        return True

    def request_shutdown(self) -> None:
        """Stop live tasks and make the process exit after the UI closes."""
        from pathlib import Path as _P
        try:
            jarvis_dir = _P(__file__).resolve().parent / ".jarvis"
            jarvis_dir.mkdir(exist_ok=True)
            (jarvis_dir / ".stop").write_text("intentional_shutdown", encoding="utf-8")
        except Exception as e:
            print(f"[Assistant] ⚠️ Could not create .stop file: {e}", flush=True)
        shutdown_requested = getattr(self, "_shutdown_requested", None)
        if shutdown_requested is None:
            self._shutdown_requested = threading.Event()
            shutdown_requested = self._shutdown_requested
        if shutdown_requested.is_set():
            return
        shutdown_requested.set()
        try:
            session = getattr(self, "session", None)
            loop = getattr(self, "_loop", None)
            if session is not None and loop is not None:
                asyncio.run_coroutine_threadsafe(session.close(), loop)
            out_queue = getattr(self, "out_queue", None)
            if out_queue is not None:
                try:
                    out_queue.put_nowait(None)
                except asyncio.QueueFull:
                    try:
                        out_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        out_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass
        except Exception as exc:
            print(f"[Assistant] ⚠️ Shutdown session close failed: {exc}")

    def _intercept_ui_tool_call(self, name: str, args: dict) -> str | None:
        """Safety net for stale models that attempt the removed quit tool action."""
        action = str(args.get("action") or "").strip().lower()
        if name != "shutdown_jarvis" and not (
            name == "jarvis_ui_control" and action == "quit_jarvis"
        ):
            return None

        transcript = str(getattr(self, "_current_input_transcript", "") or "")
        if not transcript:
            age = time.monotonic() - float(getattr(self, "_last_input_transcript_at", 0.0) or 0.0)
            if age <= 5.0:
                transcript = str(getattr(self, "_last_input_transcript", "") or "")

        if not self._is_explicit_self_quit_transcript(transcript):
            return "Ignored an unverified shutdown request. I remain online."

        self._queue_self_quit_after_farewell()
        return f'Shutdown queued. Say exactly: "{SELF_QUIT_GOODBYE}"'

    def update_voice(self, voice_name: str):
        self.voice_name = _normalize_voice_name(voice_name)
        self.ui.write_log(f"SYS: Voice change requested: {self.voice_name}")
        try:
            self.ui.sync_voice_display(self.voice_name)
        except Exception:
            pass
        if self.session and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self.session.close(), self._loop)
            except Exception as e:
                print(f"[Assistant] ⚠️ Could not close session after voice change: {e}")

    def _get_current_voice(self) -> str:
        if getattr(self, "voice_name", None):
            return _normalize_voice_name(self.voice_name)
        if hasattr(self.ui, "_voice_combo"):
            idx = self.ui._voice_combo.currentIndex()
            if idx >= 0:
                voice = self.ui._voice_combo.itemData(idx)
                if isinstance(voice, str) and voice:
                    return _normalize_voice_name(voice)
            voice = self.ui._voice_combo.currentText().strip().lower()
            if voice in SUPPORTED_VOICE_NAMES:
                return voice
        return _load_voice_name()

    async def _announce_startup(self):
        try:
            await self._safe_send_content(
                turns={"parts": [{"text": build_greeting()}]},
                turn_complete=True,
            )
        except Exception as e:
            print(f"[Assistant] Greeting failed: {e}")

    async def _send_first_greet_summary(self):
        """On first user speech, proactively inject a brief status summary."""
        await asyncio.sleep(0.5)
        try:
            import psutil
            battery = psutil.sensors_battery()
            bat_str = f"{battery.percent}% {'charging' if battery.power_plugged else 'on battery'}" if battery else "unknown"
        except Exception:
            bat_str = "unknown"
        now_str = time.strftime("%I:%M %p, %A %B %d")
        try:
            from actions.daily_briefing import get_weather_summary
            weather = await asyncio.to_thread(get_weather_summary)
            weather_str = weather.get("description", "unknown") if weather else "unknown"
            temp_str = f"{weather.get('temperature', '?')}°C" if weather else ""
        except Exception:
            weather_str = "unknown"
            temp_str = ""
        try:
            from actions.calendar_control import list_events
            cal_result = await asyncio.to_thread(list_events)
            cal_str = cal_result if cal_result else "nothing on the calendar"
        except Exception:
            cal_str = "calendar unavailable"
        summary = (
            f"[AUTO STATUS — first time user spoke] "
            f"Time: {now_str}. Battery: {bat_str}. "
            f"Weather: {weather_str} {temp_str}. "
            f"Calendar: {cal_str}. "
            f"Use this to give a quick casual greeting status."
        )
        try:
            await self._safe_send_content(
                turns={"parts": [{"text": summary}]},
                turn_complete=True,
            )
        except Exception as e:
            print(f"[Assistant] First-greet summary failed: {e}")

    def set_tour_active(self, value: bool) -> None:
        """Track the intro/tour lock state without closing the live session."""
        self._tour_active = bool(value)

    async def _wait_before_reconnect(self, delay: float) -> None:
        """Wait between reconnect attempts, aborting instantly during shutdown."""
        shutdown_requested = getattr(self, "_shutdown_requested", None)
        if shutdown_requested is not None and shutdown_requested.is_set():
            return
        wait_seconds = min(float(delay or 0.0), _LIVE_RECONNECT_MAX_DELAY)
        if shutdown_requested is None:
            await asyncio.sleep(wait_seconds)
            return
        try:
            await asyncio.wait_for(shutdown_requested.wait(), timeout=wait_seconds)
        except asyncio.TimeoutError:
            pass

    async def _execute_tool_batch(self, calls) -> list:
        """Run independent tool calls concurrently, mutating ones in order."""
        names = [getattr(call, "name", "") for call in calls]
        if any(name in _MUTATING_TOOL_NAMES for name in names):
            results = []
            for call in calls:
                results.append(await self._execute_tool(call))
            return results
        return list(await asyncio.gather(*(self._execute_tool(call) for call in calls), return_exceptions=True))

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        conv_mem = getattr(self, "_conv_memory", None)
        if conv_mem:
            conv_ctx_str = conv_mem.get_recent_context(3)
            if conv_ctx_str and conv_ctx_str != "No previous conversation history.":
                parts.append(f"\n{conv_ctx_str}\n")

        try:
            from memory.persistent_memory import build_memory_context
            pm_ctx = build_memory_context(max_chars=3000)
            if pm_ctx:
                parts.append(f"\n[PERSISTENT MEMORY]\n{pm_ctx}\n")
        except Exception:
            pass

        mood_hint = getattr(self, "_mood_analyzer", None)
        if mood_hint:
            mood_hint = mood_hint.get_adaptation_hint()
            mood_summary = self._mood_analyzer.get_summary()
            mood_ctx = (
                f"\n[MOOD CONTEXT]\n"
                f"Current user mood: {mood_summary['mood']} (confidence: {mood_summary['confidence']})\n"
                f"Energy: {mood_summary['energy']}, Stress: {mood_summary['stress']}, Fatigue: {mood_summary['fatigue']}\n"
                f"Adaptation hint: {mood_hint}\n"
                f"Conversation turns: {getattr(self, '_conversation_turn_count', 0)}\n"
                f"Adapt your behavior naturally based on this mood. Do NOT tell the user their mood unless asked.\n\n"
            )
            parts.append(mood_ctx)

        voice = self._get_current_voice()
        return types.LiveConnectConfig(
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection={
                    "silence_duration_ms": LIVE_VAD_SILENCE_MS,
                },
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        if name in ("web_search", "code_helper") and "query" in args:
            cached = get_cached_answer(args["query"])
            if cached:
                print(f"[Assistant] 🔧 {name} (CACHED)")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": cached},
                )

        print(f"[Assistant] 🔧 {name}  {args}")
        ui = self.ui

        if getattr(ui, "operational_ready", True) is False:
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Startup sequence active — tool calls are paused."},
            )

        if qa_mode.qa_enabled():
            decision = qa_mode.guard_tool_call(name, args)
            if not decision.allowed:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": qa_mode.qa_block_message(decision)},
                )

        set_state = getattr(ui, "set_state", None)
        if callable(set_state):
            try:
                set_state("THINKING")
            except Exception:
                pass

        intercepted = self._intercept_ui_tool_call(name, args)
        if intercepted is not None:
            return types.FunctionResponse(
                id=fc.id, name=name, response={"result": intercepted}
            )

        _tool_start = time.time()
        _slow_tools = {"deep_research", "agent_task", "create_presentation", "autonomous_worker",
                       "browser_control", "screen_auto", "system_access", "coding_assistant"}
        if name in _slow_tools:
            try:
                self._safe_send_content_sync(
                    turns={"parts": [{"text": "Working on it..."}]},
                    turn_complete=False
                )
            except Exception:
                pass

        if name == "save_memory":
            try:
                category = args.get("category", "notes")
                key      = args.get("key", "")
                value    = args.get("value", "")
                if key and value:
                    update_memory({category: {key: {"value": value}}})
                    print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            except Exception as e:
                print(f"[Memory] ⚠️ save_memory failed: {e}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Tool execution completed"

        try:
            if name == "open_app":
                from actions.open_app import open_app
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                from actions.weather_report import weather_action
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                from actions.browser_control import browser_control
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                from actions.file_controller import file_controller
                if (
                    args.get("action", "").lower() == "open"
                    and not args.get("path")
                    and not args.get("name")
                ):
                    current_file = getattr(self.ui, "current_file", None)
                    if current_file:
                        args["path"] = current_file
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "check_messages":
                from actions.message_monitor import check_messages
                r = await loop.run_in_executor(
                    None,
                    lambda: check_messages(parameters=args, response=None, player=self.ui, session_memory=None),
                )
                result = r or "No readable messages were found."

            elif name == "prepare_message_reply":
                from actions.send_message import prepare_message_reply
                r = await loop.run_in_executor(
                    None,
                    lambda: prepare_message_reply(parameters=args, response=None, player=self.ui, session_memory=None),
                )
                result = r or "The message draft could not be prepared."

            elif name == "send_message":
                from actions.send_message import send_message, prepare_message_reply
                from actions.screen_automation import handle as screen_auto_handle
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."
                # Skip screenshot verification for messaging — too slow

            elif name == "email_control":
                from actions.email_control import email_control
                if args.get("action", "").lower() == "connect" and not args.get("credentials_path"):
                    current_file = getattr(self.ui, "current_file", None)
                    if current_file and Path(str(current_file)).suffix.lower() == ".json":
                        args["credentials_path"] = current_file
                r = await loop.run_in_executor(None, lambda: email_control(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or "Email action completed."

            elif name == "reminder":
                from actions.reminder import reminder
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                from actions.youtube_video import youtube_video
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "media_control":
                from actions.media_control import media_control
                r = await loop.run_in_executor(None, lambda: media_control(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":
                from actions.screen_processor import screen_process
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None,
                            "speak": self._speak_vision_result},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                from actions.computer_settings import computer_settings
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                from actions.desktop import desktop_control
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                from actions.code_helper import code_helper
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                from actions.dev_agent import dev_agent
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(
                    goal=args.get("goal", ""),
                    priority=priority,
                    speak=self.speak,
                    immediate=True,
                )
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                from actions.web_search import web_search as web_search_action
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                from actions.file_processor import file_processor
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                from actions.computer_control import computer_control
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                from actions.game_updater import game_updater
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                from actions.flight_finder import flight_finder
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "jarvis_ui_control":
                action = str(args.get("action") or "").strip().lower()
                if action == "change_theme":
                    theme = str(args.get("theme") or "").strip().lower()
                    allowed = {"arc_reactor", "stealth_red", "vibranium_purple", "nanotech_gold", "platinum"}
                    if theme not in allowed:
                        raise ValueError(f"Unknown theme: {theme or 'missing'}")
                    self.ui.set_theme(theme)
                    result = f"Theme changed to {theme.replace('_', ' ')}."
                elif action == "change_graphics_quality":
                    quality = str(args.get("graphics_quality") or "").strip().lower()
                    if quality not in {"low", "medium", "high"}:
                        raise ValueError(f"Unknown graphics quality: {quality or 'missing'}")
                    self.ui.set_graphics_quality(quality)
                    result = f"Graphics quality changed to {quality}."
                else:
                    self.ui.handle_ui_command(action)
                    result = f"Interface action completed: {action.replace('_', ' ')}."

            elif name == "deep_research":
                from actions.deep_research import request_deep_research
                r = request_deep_research(parameters=args, player=self.ui, speak=self.speak)
                result = r or "Deep research preference requested."

            elif name == "create_presentation":
                from actions.presentation_maker import request_presentation
                current_file = getattr(self.ui, "current_file", None)
                supported_sources = {
                    ".txt", ".md", ".rst", ".csv", ".json", ".jsonl", ".docx", ".pptx",
                    ".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp",
                    ".wav", ".mp3", ".m4a", ".mp4", ".mov", ".avi", ".webm",
                }
                if (
                    not args.get("source_file")
                    and not args.get("source_files")
                    and current_file
                    and Path(str(current_file)).suffix.lower() in supported_sources
                ):
                    args["source_files"] = [current_file]
                r = request_presentation(parameters=args, player=self.ui, speak=self.speak)
                result = r or "Presentation preference requested."

            elif name == "task_status":
                from agent.task_queue import get_queue

                queue = get_queue()
                action = str(args.get("action") or "get").lower()
                task_id = str(args.get("task_id") or "").strip()
                if action == "all" or not task_id:
                    result = json.dumps(queue.get_all_statuses(), ensure_ascii=False)
                elif action == "cancel":
                    result = f"Task {task_id} cancelled." if queue.cancel(task_id) else f"Task {task_id} could not be cancelled."
                else:
                    status = queue.get_status(task_id)
                    result = json.dumps(status, ensure_ascii=False) if status else f"Task {task_id} was not found."

            elif name == "system_info":
                from actions.system_info import handle as system_info_handle
                r = await loop.run_in_executor(None, lambda: system_info_handle(parameters=args))
                result = r or "System info retrieved."

            elif name == "bluetooth_control":
                from actions.bluetooth_control import handle as bluetooth_handle
                r = await loop.run_in_executor(None, lambda: bluetooth_handle(parameters=args))
                result = r or "Bluetooth action completed."

            elif name == "wifi_control":
                from actions.wifi_control import handle as wifi_handle
                r = await loop.run_in_executor(None, lambda: wifi_handle(parameters=args))
                result = r or "WiFi action completed."

            elif name == "calendar_control":
                from actions.calendar_control import handle as calendar_handle
                r = await loop.run_in_executor(None, lambda: calendar_handle(parameters=args))
                result = r or "Calendar action completed."

            elif name == "autonomous_control":
                from actions.autonomous_agent import handle as autonomous_handle
                r = await loop.run_in_executor(None, lambda: autonomous_handle(parameters=args))
                result = r or "Autonomous control action completed."

            elif name == "market_monitor":
                from actions.market_monitor import handle as market_handle
                r = await loop.run_in_executor(None, lambda: market_handle(parameters=args))
                result = r or "Market action completed."

            elif name == "daily_briefing":
                from actions.daily_briefing import handle as briefing_handle
                r = await loop.run_in_executor(None, lambda: briefing_handle(parameters=args))
                result = r or "Briefing completed."

            elif name == "contact_manager":
                from actions.contact_manager import handle as contact_handle
                r = await loop.run_in_executor(None, lambda: contact_handle(parameters=args))
                result = r or "Contact action completed."

            elif name == "taskbar_detect":
                from actions.taskbar_detect import get_pinned_taskbar_apps, get_running_apps, is_app_running, focus_app
                action = args.get("action", "running_list")
                app_name = args.get("app_name", "")
                if action == "is_running":
                    result = f"{app_name} is {'running' if is_app_running(app_name) else 'not running'}."
                elif action == "focus":
                    result = f"{'Focused' if focus_app(app_name) else 'Could not focus'} {app_name}."
                elif action == "running_list":
                    apps = get_running_apps()
                    result = f"Running apps: {', '.join(apps[:20])}" if apps else "No apps detected."
                elif action == "pinned_list":
                    apps = get_pinned_taskbar_apps()
                    result = f"Pinned apps: {', '.join(apps[:30])}" if apps else "Could not detect pinned apps."
                else:
                    result = f"Unknown taskbar_detect action: {action}"

            elif name == "full_control":
                from actions.full_control import handle as full_control_handle
                from actions.screen_automation import handle as screen_auto_handle
                r = await loop.run_in_executor(None, lambda: full_control_handle(parameters=args))
                result = r or "System action completed."
                critical_fc = {"open_app", "close_app", "lock_screen", "sleep", "hibernate",
                               "volume_up", "volume_down", "mute", "volume_set"}
                if args.get("action", "") in critical_fc:
                    verify_desc = f"full_control {args.get('action')} {args.get('target', '') or args.get('value', '')}"
                    try:
                        vr = await loop.run_in_executor(None, lambda: screen_auto_handle(parameters={"action": "verify_action", "target": verify_desc}))
                        result += f"\n[VERIFIED] {vr}"
                    except Exception:
                        result += "\n[VERIFY SKIPPED]"

            elif name == "cybersec":
                from actions.cybersec_tools import handle as cybersec_handle
                r = await loop.run_in_executor(None, lambda: cybersec_handle(parameters=args))
                result = r or "Cybersec action completed."

            elif name == "screen_auto":
                from actions.screen_automation import handle as screen_auto_handle
                r = await loop.run_in_executor(None, lambda: screen_auto_handle(parameters=args))
                result = r or "Screen automation completed."
                # Only verify destructive/critical actions, not routine ones (speed optimization)
                verify_actions = {"close_window", "shutdown", "restart", "sleep", "lock"}
                if args.get("action", "") in verify_actions:
                    verify_desc = f"screen_auto {args.get('action')} {args.get('target', '') or args.get('value', '')}"
                    try:
                        vr = await loop.run_in_executor(None, lambda: screen_auto_handle(parameters={"action": "verify_action", "target": verify_desc}))
                        result += f"\n[VERIFIED] {vr}"
                    except Exception:
                        result += "\n[VERIFY SKIPPED]"

            elif name == "monitor":
                from actions.proactive_monitor import handle as monitor_handle
                r = await loop.run_in_executor(None, lambda: monitor_handle(parameters=args))
                result = r or "Monitor check completed."

            elif name == "cleanup":
                from actions.system_cleanup import handle as cleanup_handle
                r = await loop.run_in_executor(None, lambda: cleanup_handle(parameters=args))
                result = r or "Cleanup completed."

            elif name == "sing":
                from actions.sing import handle as sing_handle
                r = await loop.run_in_executor(None, lambda: sing_handle(params=args))
                result = r or "Singing completed."

            elif name == "proactive_tasks":
                from actions.proactive_tasks import handle as proactive_handle
                r = await loop.run_in_executor(None, lambda: proactive_handle(params=args))
                result = r or "Proactive task action completed."

            elif name == "phone_control":
                from actions.phone_control import handle as phone_handle
                from actions.screen_automation import handle as screen_auto_handle
                r = await loop.run_in_executor(None, lambda: phone_handle(params=args))
                result = r or "Phone action completed."
                verify_desc = f"{args.get('action', 'phone')} {args.get('contact', '') or args.get('number', '')}"
                try:
                    vr = await loop.run_in_executor(None, lambda: screen_auto_handle(parameters={"action": "verify_action", "target": verify_desc}))
                    result += f"\n[VERIFIED] {vr}"
                except Exception:
                    result += "\n[VERIFY SKIPPED]"

            elif name == "coding_assistant":
                from actions.coding_assistant import handle as coding_handle
                r = await loop.run_in_executor(None, lambda: coding_handle(params=args))
                result = r or "Coding action completed."

            elif name == "learning_memory":
                from actions.learning_memory import handle as memory_handle
                r = await loop.run_in_executor(None, lambda: memory_handle(params=args))
                result = r or "Memory action completed."

            elif name == "notification_center":
                from actions.notification_center import handle as notif_handle
                r = await loop.run_in_executor(None, lambda: notif_handle(params=args))
                result = r or "Notification action completed."

            elif name == "clipboard_manager":
                from actions.clipboard_manager import handle as clipboard_handle
                r = await loop.run_in_executor(None, lambda: clipboard_handle(params=args))
                result = r or "Clipboard action completed."

            elif name == "alarm_timer":
                from actions.alarm_timer import handle as alarm_handle
                r = await loop.run_in_executor(None, lambda: alarm_handle(params=args))
                result = r or "Alarm action completed."

            elif name == "smart_assistant":
                from actions.smart_assistant import handle as smart_handle
                r = await loop.run_in_executor(None, lambda: smart_handle(params=args))
                result = r or "Smart assistant action completed."

            elif name == "system_access":
                from actions.system_access import handle as sysaccess_handle
                r = await loop.run_in_executor(None, lambda: sysaccess_handle(parameters=args))
                result = r or "System access action completed."

            elif name == "self_control":
                from actions.self_control import handle as selfcontrol_handle
                r = await loop.run_in_executor(None, lambda: selfcontrol_handle(parameters=args))
                result = r or "Self-control action completed."

            elif name == "autonomous_brain":
                from actions.autonomous_brain import handle as autonomous_brain_handle
                r = await loop.run_in_executor(None, lambda: autonomous_brain_handle(parameters=args))
                result = r or "Autonomous brain action completed."

            elif name == "money_makers":
                from actions.money_makers import handle as money_makers_handle
                r = await loop.run_in_executor(None, lambda: money_makers_handle(parameters=args))
                result = r or "Money makers action completed."

            elif name == "gumroad_api":
                from actions.gumroad_api import handle as gumroad_api_handle
                r = await loop.run_in_executor(None, lambda: gumroad_api_handle(parameters=args))
                result = r or "Gumroad API action completed."

            elif name == "social_media":
                from actions.social_media import handle as social_media_handle
                r = await loop.run_in_executor(None, lambda: social_media_handle(parameters=args))
                result = r or "Social media action completed."

            elif name == "content_engine":
                from actions.content_engine import handle as content_engine_handle
                r = await loop.run_in_executor(None, lambda: content_engine_handle(parameters=args))
                result = r or "Content engine action completed."

            elif name == "self_evolution":
                from actions.self_evolution import handle as self_evolution_handle
                r = await loop.run_in_executor(None, lambda: self_evolution_handle(parameters=args))
                result = r or "Self evolution action completed."

            elif name == "auto_start":
                from actions.auto_start import handle as auto_start_handle
                r = await loop.run_in_executor(None, lambda: auto_start_handle(parameters=args))
                result = r or "Auto start action completed."

            elif name == "mood_status":
                action = args.get("action", "get")
                if action == "get":
                    result = self._mood_analyzer.get_summary()
                elif action == "history":
                    result = list(self._mood_analyzer._mood_history)[-20:]
                elif action == "summary":
                    result = {
                        "mood": self._mood_analyzer.get_mood(),
                        "energy": self._mood_analyzer.get_energy(),
                        "stress": self._mood_analyzer.get_stress(),
                        "fatigue": self._mood_analyzer.get_fatigue(),
                        "adaptation": self._mood_analyzer.get_adaptation_hint(),
                        "total_turns_analyzed": len(self._mood_analyzer._speech_rates),
                    }
                else:
                    result = self._mood_analyzer.get_summary()

            elif name == "screen_awareness":
                action = args.get("action", "context")
                if action == "context":
                    result = self._screen_awareness.get_current_context()
                elif action == "should_read":
                    should, reason = self._screen_awareness.should_read_screen()
                    result = {"should_read": should, "reason": reason}
                elif action == "navigation_hint":
                    user_text = args.get("user_text", "")
                    hint = self._screen_awareness.get_navigation_hint(user_text)
                    result = hint or f"User is in {self._screen_awareness._current_app or 'unknown app'}"
                elif action == "errors":
                    err = self._screen_awareness.get_error_context()
                    result = err or "No recent errors detected."
                elif action == "recent_apps":
                    result = self._screen_awareness.get_recent_apps(10)
                else:
                    result = self._screen_awareness.get_current_context()

            elif name == "real_hustle":
                action = args.get("action", "status")
                if action == "status":
                    result = self._hustle_engine.get_status()
                elif action == "ideas":
                    result = self._hustle_engine.get_hustle_ideas()
                elif action == "create_product":
                    product = self._hustle_engine.create_product(
                        args.get("type", "freelance_coding"),
                        args.get("name", "Untitled Product"),
                        args.get("description", ""),
                    )
                    result = f"Product created: {product['name']} (ID: {product['id']})"
                elif action == "record_revenue":
                    amount = args.get("amount")
                    if amount is None:
                        result = "Revenue not recorded: amount is required (e.g. amount=25)."
                    else:
                        amount = float(amount)
                        source = args.get("source", "unknown")
                        rr = self._hustle_engine.record_revenue(amount, source, args.get("description", ""))
                        if rr.get("success"):
                            result = f"Revenue recorded: ${amount:.2f} from {source}. Balance: ${self._hustle_engine._revenue['balance']:.2f}"
                        else:
                            result = f"Revenue not recorded: {rr.get('error')}"
                elif action == "withdraw":
                    if args.get("amount") is None:
                        result = "Withdrawal failed: amount is required (e.g. amount=50). Nothing was deducted."
                    else:
                        amount = float(args.get("amount"))
                        method = args.get("method", "manual")
                        if args.get("paypal_email"):
                            self._hustle_engine._payout_destination = args["paypal_email"]
                        w = self._hustle_engine.withdraw(amount, method)
                        if w["success"]:
                            note = w.get("note", "")
                            result = f"Withdrawn ${amount:.2f} via {method}. New balance: ${w['new_balance']:.2f}" + (f". {note}" if note else "")
                        else:
                            result = f"Withdrawal failed: {w['error']}"
                elif action == "earnings_report":
                    result = self._hustle_engine.get_earnings_report()
                elif action == "action_plan":
                    result = self._hustle_engine.get_action_plan()
                elif action == "track_sale":
                    name_str = args.get("product_name", "Unknown")
                    amount = args.get("amount")
                    if amount is None:
                        result = f"Sale not tracked for {name_str}: amount is required."
                    else:
                        amount = float(amount)
                        rr = self._hustle_engine.record_revenue(amount, "sale", f"Sale: {name_str}")
                        if rr.get("success"):
                            result = f"Sale tracked: {name_str} for ${amount:.2f}"
                        else:
                            result = f"Sale not tracked for {name_str}: {rr.get('error')}"
                elif action == "list_products":
                    products = self._hustle_engine._active.get("products", [])
                    if not products:
                        result = "No products yet. Use create_product to make your first."
                    else:
                        result = "\n".join(f"- {p['name']} ({p['type']}) — {p['status']}" for p in products[-10:])
                elif action == "balance":
                    result = self._hustle_engine.balance()
                elif action == "open_platform":
                    platform = args.get("platform", "upwork")
                    query = args.get("search_query", "")
                    result = self._hustle_engine.open_platform(platform, query)
                elif action == "open_gig_search":
                    skill = args.get("skill", "python")
                    result = self._hustle_engine.open_gig_search(skill)
                else:
                    result = f"Unknown hustle action: {action}"

            elif name == "autonomous_worker":
                from actions.autonomous_worker import AutonomousWorker
                aw = AutonomousWorker()
                result = await loop.run_in_executor(None, lambda: aw.handle(args))

            elif name == "account_manager":
                from actions.account_manager import handle as acct_handle
                r = await loop.run_in_executor(None, lambda: acct_handle(params=args))
                result = r or "Account action completed."

            elif name == "noise_filter":
                from actions.noise_filter import SpeechNoiseFilter
                nf = SpeechNoiseFilter()
                result = f"NoiseFilter ready. Methods: process(audio_ndarray), reset()."

            elif name == "instagram_browser":
                from actions.instagram_browser import prepare_instagram_draft, send_instagram_draft, clear_instagram_draft, read_instagram_open_chat
                action = args.get("action", "help")
                if action == "open_chat":
                    result = read_instagram_open_chat()
                elif action == "prepare_draft":
                    result = prepare_instagram_draft(args.get("username", ""), args.get("message", ""))
                elif action == "send":
                    result = send_instagram_draft()
                elif action == "clear_draft":
                    result = clear_instagram_draft()
                else:
                    result = "InstagramBrowser: open_chat|prepare_draft|send|clear_draft"

            elif name == "safe_text_entry":
                from actions.safe_text_entry import safe_type_text, safe_type_then_enter, validate_safe_text_target
                action = args.get("action", "validate")
                text = args.get("text", "")
                if action == "type_text":
                    result = safe_type_text(text)
                elif action == "type_enter":
                    result = safe_type_then_enter(text)
                elif action == "validate":
                    result = validate_safe_text_target()
                else:
                    result = "SafeTextEntry: type_text|type_enter|validate"

            elif name == "camera_control":
                from actions.camera_control import handle as camera_handle
                result = await loop.run_in_executor(None, lambda: camera_handle(args))

            elif name == "phone_tracking":
                from actions.phone_tracking import handle as phone_handle
                result = await loop.run_in_executor(None, lambda: phone_handle(args))

            elif name == "smart_home":
                from actions.smart_home import handle as smarthome_handle
                result = await loop.run_in_executor(None, lambda: smarthome_handle(args))

            elif name == "vehicle_control":
                from actions.vehicle_control import handle as vehicle_handle
                result = await loop.run_in_executor(None, lambda: vehicle_handle(args))

            elif name == "cybersecurity":
                from actions.cybersecurity import handle as security_handle
                result = await loop.run_in_executor(None, lambda: security_handle(args))

            elif name == "data_analysis":
                from actions.data_analysis import handle as data_handle
                result = await loop.run_in_executor(None, lambda: data_handle(args))

            elif name == "automation_engine":
                from actions.automation_engine import handle as auto_handle
                result = await loop.run_in_executor(None, lambda: auto_handle(args))

            elif name == "stripe_payments":
                from actions.stripe_payments import handle as stripe_handle
                result = await loop.run_in_executor(None, lambda: stripe_handle(args))

            elif name == "jarvis_file_stamp":
                from actions.jarvis_file_stamp import mark_created_file, stamp_text_content, can_embed_stamp, write_sidecar_metadata
                action = args.get("action", "help")
                fp = args.get("file_path", "")
                context = args.get("context", "Created by JARVIS")
                if action == "stamp" and fp:
                    result = mark_created_file(Path(fp), context)
                elif action == "check" and fp:
                    result = f"Can embed stamp: {can_embed_stamp(Path(fp))}"
                elif action == "stamp_text" and args.get("content"):
                    result = stamp_text_content(args["content"], Path(fp or "output.txt"), context)
                else:
                    result = "FileStamp: stamp|check|stamp_text"

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[Assistant] 📤 {name} → {str(result)[:80]}")

        try:
            _track_ok = "ERROR" not in str(result).upper()[:20] and "FAILED" not in str(result).upper()[:20]
            from actions.learning_memory import track_pattern, set_context
            track_pattern(name, str(args.get("action", "")), "success" if _track_ok else "error")
            if name in ("send_message", "phone_control"):
                set_context("last_communication", f"{name}:{args.get('contact', '') or args.get('receiver', '')}")
            elif name == "coding_assistant":
                set_context("last_code_action", str(args.get("action", "")))
            elif name == "screen_auto":
                set_context("last_screen_action", str(args.get("action", "")))
        except Exception:
            pass

        try:
            _tool_elapsed = time.time() - _tool_start if '_tool_start' in dir() else 0
            if _tool_elapsed > 5.0 and name in _slow_tools:
                try:
                    self._safe_send_content_sync(
                        turns={"parts": [{"text": f"Done! Took {_tool_elapsed:.0f} seconds."}]},
                        turn_complete=False
                    )
                except Exception:
                    pass
            if name in ("web_search", "code_helper") and result and "query" in args:
                try:
                    save_cached_answer(args["query"], str(result)[:1200])
                except Exception:
                    pass
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": result}
            )
        except Exception as e:
            print(f"[Assistant] FunctionResponse error: {e}")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": str(result)[:500] if result else "Error creating response"}
            )

    async def _safe_send(self, coro_fn):
        async with self._send_lock:
            return await coro_fn()

    async def _safe_send_content(self, turns, turn_complete=False):
        if not self.session:
            return
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                await self.session.send_client_content(turns=turns, turn_complete=turn_complete)
                return
            except Exception as e:
                msg = str(e)
                if any(code in msg for code in ("1000", "1006", "1007", "1011", "1012")):
                    self.session = None
                    return
                raise

    def _safe_send_content_sync(self, turns, turn_complete=False):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self._safe_send_content(turns=turns, turn_complete=turn_complete),
            self._loop
        )

    async def _send_realtime(self):
        while True:
            if self._shutdown_requested.is_set():
                return
            msg = await self.out_queue.get()
            if msg is None or self._shutdown_requested.is_set():
                return
            try:
                if not self.session:
                    return
                if self._send_lock is None:
                    self._send_lock = asyncio.Lock()
                async with self._send_lock:
                    await self.session.send_realtime_input(
                        audio=types.Blob(data=msg["data"], mime_type=msg["mime_type"])
                    )
                self._last_keepalive_activity = time.monotonic()
            except Exception as e:
                msg_str = str(e)
                if any(code in msg_str for code in ("1000", "1006", "1007", "1011", "1012", "1014")):
                    self.session = None
                    return
                if "ConnectionClosed" in type(e).__name__ or "connection is closed" in msg_str.lower():
                    self.session = None
                    return
                print(f"[Assistant] ⚠️ Send error: {type(e).__name__}: {str(e)[:120]}", flush=True)
                self.session = None

    async def _listen_audio(self):
        import numpy as np
        loop = asyncio.get_event_loop()
        gain = 10 ** (_MIC_GAIN_DB / 20.0)
        agc_level = _MIC_AGC_TARGET

        mic_device = _MIC_DEVICE_ID
        if mic_device is None:
            try:
                devs = sd.query_devices()
                candidates = []
                for i, d in enumerate(devs):
                    if d['max_input_channels'] < 1:
                        continue
                    if 'stereo mix' in d['name'].lower():
                        continue
                    candidates.append((i, d))

                working_device = None
                for idx, dev in candidates:
                    try:
                        test_audio = []
                        def test_cb(indata, frames, time_info, status):
                            test_audio.append(indata.copy())
                        sr = int(dev.get('default_samplerate', SEND_SAMPLE_RATE))
                        with sd.InputStream(samplerate=sr, channels=1, dtype='int16',
                                            blocksize=512, callback=test_cb, device=idx):
                            import time as _t
                            _t.sleep(0.3)
                        if test_audio:
                            all_audio = np.concatenate(test_audio)
                            rms = float(np.sqrt(np.mean(all_audio.astype(np.float32) ** 2)))
                            if rms > 5:
                                working_device = idx
                                print(f"[Assistant] Mic found: device {idx} ({dev['name']}) rms={rms:.1f}")
                                break
                    except Exception:
                        pass

                if working_device is not None:
                    mic_device = working_device
                else:
                    mic_device = None
                    print("[Assistant] No working mic found via InputStream. Using default.")
            except Exception as e:
                print(f"[Assistant] Mic detection error: {e}")
                mic_device = None

        print("[Assistant] Mic started", flush=True)

        def callback(indata, frames, time_info, status):
            if self.ui.muted:
                return
            raw = indata.astype(np.float32)

            rms = np.sqrt(np.mean(raw ** 2)) + 1e-6

            with self._mic_energy_lock:
                self._mic_energy_level = float(rms)

            self._mood_analyzer.update_realtime_volume(rms)

            if rms < _MIC_NOISE_GATE_THRESHOLD / 32768.0:
                return

            if self._is_speaking:
                now_mono = time.monotonic()
                since_playback_start = now_mono - getattr(self, '_playback_started_at', now_mono)
                since_barge_in = now_mono - getattr(self, '_last_barge_in_time', 0.0)
                if since_playback_start > 1.2 and since_barge_in > 1.5:
                    playback_level = getattr(self, '_playback_energy', 0.0)
                    echo_threshold = max(playback_level * 3.0, 2000 / 32768.0)
                    if rms > echo_threshold:
                        self._barge_in_event.set()
                        self._last_barge_in_time = now_mono
                        print(f"[Assistant] 🛑 Barge-in (mic={rms:.0f} > threshold={echo_threshold:.0f}, playback={playback_level:.0f})")
                        if self._turn_done_event:
                            self._turn_done_event.clear()

            current_gain = gain
            if rms * gain > 0:
                actual_rms = rms * gain
                if actual_rms > agc_level * 1.2:
                    current_gain *= agc_level / actual_rms
                elif actual_rms < agc_level * 0.5:
                    current_gain *= min(agc_level / actual_rms, gain * 4)

            amplified = np.clip(raw * current_gain, -32768, 32767).astype(np.int16)
            data = amplified.tobytes()
            frame = {"data": data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
            def _safe_put():
                try:
                    self.out_queue.put_nowait(frame)
                except asyncio.QueueFull:
                    try:
                        self.out_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        self.out_queue.put_nowait(frame)
                    except asyncio.QueueFull:
                        pass
            loop.call_soon_threadsafe(_safe_put)

        try:
            devices_to_try = [mic_device, None] if mic_device is not None else [None]
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d['max_input_channels'] > 0 and 'stereo mix' not in d['name'].lower():
                    if i not in devices_to_try:
                        devices_to_try.append(i)

            opened = False
            for dev_id in devices_to_try:
                dev_info = devs[dev_id] if dev_id is not None and dev_id < len(devs) else None
                native_rate = int(float(dev_info.get('default_samplerate', SEND_SAMPLE_RATE))) if dev_info else SEND_SAMPLE_RATE
                rates_to_try = [native_rate, SEND_SAMPLE_RATE, 44100, 48000]
                rates_to_try = list(dict.fromkeys(rates_to_try))
                for try_rate in rates_to_try:
                    try:
                        stream_kwargs = dict(
                            samplerate=try_rate,
                            channels=CHANNELS,
                            dtype="int16",
                            blocksize=CHUNK_SIZE,
                            callback=callback,
                        )
                        if dev_id is not None:
                            stream_kwargs["device"] = dev_id
                        stream = sd.InputStream(**stream_kwargs)
                        stream.start()
                        dev_name = dev_info['name'] if dev_info else "default"
                        print(f"[Assistant] Mic stream open (device {dev_id}: {dev_name}, {try_rate}Hz)")
                        opened = True
                        try:
                            while not self._shutdown_requested.is_set():
                                await asyncio.sleep(0.1)
                        finally:
                            stream.stop()
                            stream.close()
                        break
                    except Exception:
                        continue
                if opened:
                    break

            if not opened:
                print("[Assistant] Could not open any microphone. Running without mic.")
                while not self._shutdown_requested.is_set():
                    await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[Assistant] Mic error: {e}")
            while not self._shutdown_requested.is_set():
                await asyncio.sleep(1)

    async def _receive_audio(self):
        print("[Assistant] 👂 Recv started", flush=True)
        out_buf, in_buf = [], []
        _new_turn = True
        turn_had_audio = False

        try:
            while True:
                if self._shutdown_requested.is_set():
                    return
                if not self.session:
                    await asyncio.sleep(0.5)
                    continue
                async for response in self.session.receive():
                    self._last_keepalive_activity = time.monotonic()

                    audio = _live_response_audio_bytes(response)
                    if not audio:
                        try:
                            import io as _io, contextlib as _ctx
                            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                                audio = response.data or b""
                        except Exception:
                            audio = b""
                    if audio:
                        turn_had_audio = True
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        try:
                            self.audio_in_queue.put_nowait(audio)
                        except asyncio.QueueFull:
                            try:
                                self.audio_in_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            self.audio_in_queue.put_nowait(audio)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                                self._interrupted_text = " ".join(out_buf)
                                if not self.ui.muted:
                                    if _new_turn:
                                        self.ui.clear_subtitle()
                                        _new_turn = False
                                    self.ui.show_subtitle(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                if not in_buf:
                                    self._current_input_transcript = ""
                                    self._mood_analyzer.start_turn()
                                    self.ui.set_mic_state("detecting")
                                in_buf.append(txt)
                                self._current_input_transcript = " ".join(in_buf).strip()
                                self._last_user_speech_at = time.monotonic()
                                ctx = self._detect_barge_in_context(self._current_input_transcript)
                                if ctx == "barge_in":
                                    print(f"[Assistant] 🛑 Barge-in detected during speech")
                                elif ctx == "direct_address":
                                    print(f"[Assistant] 🎯 User addressing JARVIS directly")
                                if (
                                    not getattr(self, "_pending_self_quit", False)
                                    and self._is_explicit_self_quit_transcript(self._current_input_transcript)
                                ):
                                    self._queue_self_quit_after_farewell()

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self._current_input_transcript = full_in
                                self._last_input_transcript = full_in
                                self._last_input_transcript_at = time.monotonic()
                                self._conversation_turn_count += 1
                                self._last_user_speech_at = time.monotonic()
                                word_count = len(full_in.split())
                                avg_vol = self._mood_analyzer._current_volume if hasattr(self._mood_analyzer, '_current_volume') else 0.0
                                self._mood_analyzer.end_turn(word_count, avg_vol)
                                mood_info = self._mood_analyzer.get_summary()
                                if mood_info["confidence"] > 0.6:
                                    print(f"[Assistant] 🧠 Mood: {mood_info['mood']} (energy={mood_info['energy']}, stress={mood_info['stress']})")
                                if (
                                    not getattr(self, "_pending_self_quit", False)
                                    and self._is_explicit_self_quit_transcript(full_in)
                                ):
                                    self._queue_self_quit_after_farewell()
                                self.ui.write_log(f"You: {full_in}")
                                if not self._first_greet_done:
                                    self._first_greet_done = True
                                    self._tg.create_task(self._send_first_greet_summary())
                            in_buf = []
                            self.ui.set_mic_state("listening")

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Assistant: {full_out}")
                            if full_in and full_out:
                                mood = self._mood_analyzer.get_mood()
                                self._conv_memory.record_turn(full_in, full_out, mood)
                                try:
                                    from memory.persistent_memory import log_conversation
                                    log_conversation(full_in, full_out, {"mood": str(mood)})
                                except Exception:
                                    pass
                            if (
                                getattr(self, "_pending_self_quit", False)
                                and (full_out or turn_had_audio)
                            ):
                                self._mark_self_quit_farewell_received()
                                
                            out_buf = []
                            turn_had_audio = False
                            _new_turn = True

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[Assistant] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        if not self.session:
                            return
                        try:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                        except Exception as te:
                            msg = str(te).lower()
                            if any(k in msg for k in ("1006", "1007", "1011", "1012", "1014",
                                                       "keepalive", "connection closed", "invalid")):
                                return
                            raise
                    if self._shutdown_requested.is_set():
                        return
        except Exception as e:
            if genai is not None and isinstance(e, genai.errors.APIError) and "1000" in str(e):
                print("[Assistant] 🔌 Session closed normally.", flush=True)
                return
            msg = str(e).lower()
            if "content_type_audio" in msg or "response_modalities" in msg:
                raise
            if any(k in msg for k in ("1000", "1006", "1007", "1011", "1012", "1014",
                                        "keepalive", "connection closed", "no close frame",
                                        "invalid")):
                print(f"[Assistant] ⚠️ Receive loop exit: {type(e).__name__}: {str(e)[:120]}", flush=True)
                self.session = None
                return
            print(f"[Assistant] ❌ Receive loop error: {type(e).__name__}: {str(e)[:200]}", flush=True)
            self.session = None
            return



    async def _play_audio(self):
        print("[Assistant] Play started", flush=True)
        import numpy as _np

        if sd is None:
            print("[Assistant] sounddevice not available, skipping audio playback")
            return

        play_chunk = CHUNK_SIZE * 2
        try:
            stream = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=play_chunk,
            )
            stream.start()
        except Exception as e:
            print(f"[Assistant] Failed to open playback stream: {e}")
            return
        _audio_streams.append(stream)

        prebuf = []
        prebuf_target = 1
        prebuffering = True
        _STUCK_SPEAKING_TIMEOUT = 5.0
        _TURN_DONE_GRACE_SECS = 2.0
        _last_audio_at = time.monotonic()
        _turn_done_at: float | None = None

        try:
            while True:
                if self._shutdown_requested.is_set():
                    return

                if self._barge_in_event.is_set():
                    self._barge_in_event.clear()
                    self.set_speaking(False)
                    while not self.audio_in_queue.empty():
                        try:
                            self.audio_in_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    prebuf.clear()
                    prebuffering = True
                    if self._turn_done_event:
                        self._turn_done_event.clear()
                    _turn_done_at = None
                    _last_audio_at = time.monotonic()
                    self.ui.set_mic_state("barge_in")
                    print("[Assistant] 🛑 Barge-in: stopped playback")
                    continue

                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.04
                    )
                    _last_audio_at = time.monotonic()
                    _turn_done_at = None
                except asyncio.TimeoutError:
                    now = time.monotonic()

                    if self._is_speaking and (now - _last_audio_at) > _STUCK_SPEAKING_TIMEOUT:
                        print("[Assistant] ⚠️ Watchdog: stuck-speaking timeout, stopping playback")
                        self.set_speaking(False)
                        if self._turn_done_event is not None:
                            self._turn_done_event.clear()
                        _turn_done_at = None
                        prebuf.clear()
                        prebuffering = True
                        if self._complete_self_quit_after_audio():
                            return
                        continue

                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                    ):
                        if _turn_done_at is None:
                            _turn_done_at = now
                        if (now - _turn_done_at) >= _TURN_DONE_GRACE_SECS:
                            if prebuffering and prebuf:
                                for c in prebuf:
                                    await asyncio.to_thread(stream.write, c)
                                prebuf.clear()
                            self.set_speaking(False)
                            self._turn_done_event.clear()
                            _turn_done_at = None
                            prebuffering = True
                            if self._complete_self_quit_after_audio():
                                return
                    continue

                if self._tts_engine and self._ext_tts_provider and self._ext_tts_provider != "gemini":
                    pass
                else:
                    if prebuffering:
                        prebuf.append(chunk)
                        if len(prebuf) >= prebuf_target:
                            prebuffering = False
                            self._playback_started_at = time.monotonic()
                            self.set_speaking(True)
                            for c in prebuf:
                                await asyncio.to_thread(stream.write, c)
                            prebuf.clear()
                    else:
                        if not self._is_speaking:
                            self._playback_started_at = time.monotonic()
                        self.set_speaking(True)
                        try:
                            chunk_arr = _np.frombuffer(chunk, dtype=_np.int16).astype(_np.float32)
                            chunk_rms = float(_np.sqrt(_np.mean(chunk_arr ** 2)) + 1e-6)
                            prev = getattr(self, '_playback_energy', 0.0)
                            self._playback_energy = prev * 0.85 + chunk_rms * 0.15
                        except Exception:
                            pass
                        await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[Assistant] ❌ Playback error: {type(e).__name__}: {str(e)[:120]}", flush=True)
            return
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def _keepalive_ping(self):
        consecutive_failures = 0
        self._last_keepalive_activity = time.monotonic()
        while True:
            await asyncio.sleep(_LIVE_KEEPALIVE_INTERVAL)
            if self._shutdown_requested.is_set() or not self.session:
                return
            idle_time = time.monotonic() - self._last_keepalive_activity
            if idle_time < _LIVE_KEEPALIVE_INTERVAL * 0.8:
                consecutive_failures = 0
                continue
            try:
                silence = b"\x00" * (SEND_SAMPLE_RATE * 2 // 5)
                await self.session.send_realtime_input(
                    audio=types.LiveInput(
                        data=silence,
                        mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                    )
                )
                consecutive_failures = 0
                self._last_keepalive_activity = time.monotonic()
            except Exception as e:
                consecutive_failures += 1
                if consecutive_failures > 3:
                    print("[Assistant] ⚠️  Keepalive failed — forcing reconnect")
                    self.session = None
                    return
                await asyncio.sleep(1)

    async def _periodic_screen_watch(self):
        """Fast active-window tracking every 5 seconds (no screenshot)."""
        while True:
            await asyncio.sleep(5)
            if self._shutdown_requested.is_set():
                return
            try:
                await asyncio.to_thread(self._screen_awareness.refresh)
            except Exception:
                pass

    async def _periodic_vision(self):
        """Periodically capture screen for constant visual awareness."""
        while True:
            await asyncio.sleep(20)
            if self._shutdown_requested.is_set():
                return
            try:
                await asyncio.to_thread(self._do_background_vision)
            except Exception:
                pass

    def _do_background_vision(self):
        try:
            import hashlib
            from actions.screen_processor import _capture_screen
            image_bytes, mime = _capture_screen()
            if image_bytes and len(image_bytes) > 100:
                new_hash = hashlib.md5(image_bytes).hexdigest()[:16]
                old_hash = getattr(self, "_prev_screen_hash", "")
                self._last_screen_snapshot = image_bytes
                self._last_screen_mime = mime
                self._last_vision_time = time.time()
                active_app = self._screen_awareness.get_active_window_title()
                self._screen_awareness.update(active_app, new_hash, "")
                if old_hash and new_hash != old_hash:
                    now = time.time()
                    last_change = getattr(self, "_last_screen_change_time", 0.0)
                    if now - last_change > 120:
                        self._last_screen_change_time = now
                        self._prev_screen_hash = new_hash
                        try:
                            loop = self._loop
                            if loop and loop.is_running():
                                loop.call_soon_threadsafe(
                                    asyncio.ensure_future,
                                    self._alert_screen_change(),
                                )
                        except Exception:
                            pass
                    else:
                        self._prev_screen_hash = new_hash
                else:
                    self._prev_screen_hash = new_hash
        except Exception:
            pass

    async def _alert_screen_change(self):
        """Proactively send the screenshot to the AI so it can analyze what changed."""
        try:
            if not self.session or self._shutdown_requested.is_set():
                return
            image_bytes = getattr(self, "_last_screen_snapshot", b"")
            if not image_bytes or len(image_bytes) < 200:
                return
            from google.genai import types as gtypes
            import io
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes))
                img.thumbnail((640, 360))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=60)
                compressed = buf.getvalue()
                mime = "image/jpeg"
            except ImportError:
                compressed = image_bytes[:100000]
                mime = "image/png"
            parts = [
                gtypes.Part.from_bytes(data=compressed, mime_type=mime),
                gtypes.Part(text=(
                    "[AUTO VISION] The user's screen changed significantly. "
                    "Look at this screenshot and briefly mention what you see "
                    "if something interesting or important appeared. "
                    "Otherwise say nothing."
                )),
            ]
            await self._safe_send_content(
                turns=gtypes.Content(role="user", parts=parts),
                turn_complete=True,
            )
        except Exception:
            pass

    async def _alert_new_message(self, app_names: str):
        """Notify the model that a messaging app opened."""
        try:
            if not self.session or self._shutdown_requested.is_set():
                return
            await self._safe_send_content(
                turns={"parts": [{"text": (
                    f"[AUTO MESSAGE ALERT] A messaging app just opened: {app_names}. "
                    "Offer to help the user send or check messages."
                )}]},
                turn_complete=True,
            )
        except Exception:
            pass

    async def _alert_upcoming_event(self, event_line: str, minutes_until: int):
        """Notify the model of an upcoming calendar event."""
        try:
            if not self.session or self._shutdown_requested.is_set():
                return
            await self._safe_send_content(
                turns={"parts": [{"text": (
                    f"[AUTO CALENDAR REMINDER] An event starts in {minutes_until} minutes: {event_line}. "
                    "Casually remind the user about this upcoming event."
                )}]},
                turn_complete=True,
            )
        except Exception:
            pass

    async def _fire_scheduled_alert(self, message: str):
        """Fire a scheduled notification alert."""
        try:
            if not self.session or self._shutdown_requested.is_set():
                return
            await self._safe_send_content(
                turns={"parts": [{"text": (
                    f"[SCHEDULED ALERT] {message}\n"
                    "Notify the user about this alert in a casual way."
                )}]},
                turn_complete=True,
            )
        except Exception:
            pass

    async def _autonomous_monitor(self):
        """Background monitoring: system health, battery, messages, calendar, CPU, network."""
        try:
            import psutil
        except ImportError:
            return
        last_battery_check = 0
        last_health_check = 0
        last_network_check = 0
        last_cpu_check = 0
        last_msg_check = 0
        last_cal_check = 0
        BATTERY_INTERVAL = 120
        HEALTH_INTERVAL = 300
        NETWORK_INTERVAL = 600
        CPU_INTERVAL = 60
        MSG_CHECK_INTERVAL = 30
        CAL_CHECK_INTERVAL = 120
        CTX_CHECK_INTERVAL = 60
        low_battery_warned = False
        _prev_msg_apps: set[str] = set()
        _last_cal_alert_time = 0.0
        last_ctx_check = 0.0

        while True:
            await asyncio.sleep(15)
            if self._shutdown_requested.is_set():
                return
            now = time.time()

            if now - last_battery_check > BATTERY_INTERVAL:
                last_battery_check = now
                try:
                    bat = psutil.sensors_battery()
                    if bat:
                        if not bat.power_plugged and bat.percent < 20 and not low_battery_warned:
                            low_battery_warned = True
                            self.ui.write_log(f"SYS: Battery LOW: {bat.percent}% — plug in!")
                            try:
                                from actions.notification_center import push_notification
                                push_notification({"title": "Battery Low", "message": f"Battery at {bat.percent}% — plug in!", "level": "warning", "source": "monitor"})
                            except Exception:
                                pass
                        elif bat.power_plugged:
                            low_battery_warned = False
                except Exception:
                    pass

            if now - last_health_check > HEALTH_INTERVAL:
                last_health_check = now
                try:
                    from actions.autonomous_agent import _check_disk_space
                    alerts = _check_disk_space()
                    for alert in alerts:
                        self.ui.write_log(f"SYS: {alert.get('message', 'Health alert')}")
                except Exception:
                    pass

            if now - last_cpu_check > CPU_INTERVAL:
                last_cpu_check = now
                try:
                    cpu = psutil.cpu_percent(interval=0.1)
                    if cpu > 90:
                        self.ui.write_log(f"SYS: CPU high: {cpu}%")
                        try:
                            from actions.notification_center import push_notification
                            push_notification({"title": "CPU High", "message": f"CPU at {cpu}%", "level": "warning", "source": "monitor"})
                        except Exception:
                            pass
                except Exception:
                    pass

            if now - last_network_check > NETWORK_INTERVAL:
                last_network_check = now
                try:
                    net = psutil.net_io_counters()
                    if hasattr(self, '_last_net_bytes'):
                        sent_diff = net.bytes_sent - self._last_net_bytes[0]
                        recv_diff = net.bytes_recv - self._last_net_bytes[1]
                        if recv_diff > 100 * 1024 * 1024:
                            mb = recv_diff // (1024*1024)
                            self.ui.write_log(f"SYS: High download: {mb}MB")
                            try:
                                from actions.notification_center import push_notification
                                push_notification({"title": "High Download", "message": f"{mb}MB downloaded", "level": "info", "source": "monitor"})
                            except Exception:
                                pass
                    self._last_net_bytes = (net.bytes_sent, net.bytes_recv)
                except Exception:
                    pass

            if now - last_msg_check > MSG_CHECK_INTERVAL:
                last_msg_check = now
                try:
                    current_title = self._screen_awareness.get_active_window_title().lower()
                    msg_apps = ("whatsapp", "discord", "telegram", "signal", "instagram")
                    if any(app in current_title for app in msg_apps):
                        if current_title not in _prev_msg_apps and not self._shutdown_requested.is_set():
                            self.ui.write_log(f"SYS: Messaging app opened: {current_title}")
                            try:
                                if self._loop and self._loop.is_running():
                                    asyncio.ensure_future(self._alert_new_message(current_title))
                            except Exception:
                                pass
                    _prev_msg_apps = {current_title}
                except Exception:
                    pass

            if now - last_cal_check > CAL_CHECK_INTERVAL:
                last_cal_check = now
                try:
                    import datetime
                    now_dt = datetime.datetime.now()
                    soon = now_dt + datetime.timedelta(minutes=15)
                    from actions.calendar_control import list_events
                    result = list_events()
                    if result and "no events" not in result.lower() and "unavailable" not in result.lower():
                        for line in result.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
                                    try:
                                        time_part = line.split(" - ")[0].strip() if " - " in line else line.split()[0]
                                        event_time = datetime.datetime.strptime(time_part, fmt).replace(
                                            year=now_dt.year, month=now_dt.month, day=now_dt.day
                                        )
                                        diff_min = (event_time - now_dt).total_seconds() / 60
                                        if 0 < diff_min <= 15 and now - _last_cal_alert_time > 600:
                                            _last_cal_alert_time = now
                                            self.ui.write_log(f"SYS: Upcoming event: {line}")
                                            if self._loop and self._loop.is_running():
                                                asyncio.ensure_future(self._alert_upcoming_event(line, int(diff_min)))
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass
                except Exception:
                    pass

            if now - last_cal_check > CAL_CHECK_INTERVAL:
                last_cal_check = now
                try:
                    from actions.proactive_tasks import get_pending_jobs
                    pending = get_pending_jobs()
                    for job in pending[:2]:
                        job_id = job.get("id", "")
                        job_type = job.get("type", "")
                        desc = job.get("description", "")
                        self.ui.write_log(f"SYS: Running proactive job: {desc}")
                        if self._loop and self._loop.is_running():
                            asyncio.ensure_future(self._run_proactive_job(job_id, job_type, desc))
                except Exception:
                    pass

                try:
                    from actions.notification_center import check_due_alerts
                    due_alerts = check_due_alerts()
                    for alert in due_alerts[:3]:
                        msg = alert.get("message", "Alert")
                        self.ui.write_log(f"SYS: Alert: {msg}")
                        if self._loop and self._loop.is_running():
                            asyncio.ensure_future(self._fire_scheduled_alert(msg))
                except Exception:
                    pass

            if now - last_ctx_check > CTX_CHECK_INTERVAL:
                last_ctx_check = now
                try:
                    title = self._screen_awareness.refresh()
                    if title and title != "Unknown":
                        tl = title.lower()
                        ctx = "general"
                        if any(k in tl for k in ("vscode", "pycharm", "sublime", "notepad++", "code", ".py", ".js", ".html")):
                            ctx = "coding"
                        elif any(k in tl for k in ("chrome", "firefox", "edge", "browser")):
                            ctx = "browsing"
                        elif any(k in tl for k in ("whatsapp", "discord", "telegram", "signal", "teams", "slack")):
                            ctx = "messaging"
                        elif any(k in tl for k in ("word", "excel", "powerpoint", "docs", "sheets")):
                            ctx = "document_work"
                        elif any(k in tl for k in ("photoshop", "figma", "canva", "paint")):
                            ctx = "design"
                        elif any(k in tl for k in ("spotify", "youtube", "vlc", "media")):
                            ctx = "media"
                        from actions.learning_memory import set_context
                        set_context("current_activity", ctx)
                        set_context("active_window", title[:100])
                except Exception:
                    pass

    async def _run_proactive_job(self, job_id: str, job_type: str, description: str):
        """Execute a proactive job by injecting it into the live session."""
        try:
            if not self.session or self._shutdown_requested.is_set():
                return
            prompt = (
                f"[AUTO PROACTIVE JOB] Execute this task: {description}\n"
                f"Job type: {job_type}\n"
                "Do it now. Use whatever tools are needed. Report what you did."
            )
            await self._safe_send_content(
                turns={"parts": [{"text": prompt}]},
                turn_complete=True,
            )
            from actions.proactive_tasks import mark_job_run
            mark_job_run(job_id)
        except Exception as e:
            print(f"[Assistant] Proactive job failed: {e}")

    async def _mood_checkin_loop(self):
        """Periodically check mood — passive only, no proactive engagement."""
        while True:
            await asyncio.sleep(60)
            if self._shutdown_requested.is_set():
                return
            try:
                self._mood_analyzer.get_mood()
            except Exception:
                pass

    async def _money_making_loop(self):
        """Autonomous money loop. JARVIS builds products, deploys storefront, finds+applies to jobs."""
        import random
        last_full_cycle = 0
        last_build = 0
        last_deploy = 0
        FULL_CYCLE_INT = 90
        BUILD_INT = 60
        DEPLOY_INT = 120
        self.ui.write_log("SYS: Autonomous worker online. Making money.")
        while True:
            await asyncio.sleep(15)
            if self._shutdown_requested.is_set():
                return
            now = time.time()
            try:
                loop = asyncio.get_event_loop()

                # Build a product every 2 minutes
                if now - last_build > BUILD_INT:
                    last_build = now
                    try:
                        from actions.autonomous_worker import AutonomousWorker
                        aw = AutonomousWorker()
                        work_types = ["python_script", "web_scraper", "cli_tool", "flask_api",
                                      "automation_script", "data_pipeline", "saas_template"]
                        wt = random.choice(work_types)
                        result = await loop.run_in_executor(None, lambda: aw.do_work(wt, f"Auto-built {wt}"))
                        self.ui.write_log(f"SYS: Built {wt}: {str(result)[:60]}")
                    except Exception as e:
                        print(f"[Worker] Build error: {e}")

                # Deploy storefront + git push every 4 minutes
                if now - last_deploy > DEPLOY_INT:
                    last_deploy = now
                    try:
                        from actions.autonomous_worker import AutonomousWorker
                        aw = AutonomousWorker()
                        result = await loop.run_in_executor(None, lambda: aw.deploy())
                        self.ui.write_log(f"SYS: Deploy: {str(result)[:70]}")
                    except Exception as e:
                        print(f"[Worker] Deploy error: {e}")

                # Full brain cycle (apply jobs, evolve, research) every 3 minutes
                if now - last_full_cycle > FULL_CYCLE_INT:
                    last_full_cycle = now
                    try:
                        from actions.autonomous_brain import handle as bh
                        result = await loop.run_in_executor(None, lambda: bh({"action": "run_full_cycle"}))
                        lines = [l for l in result.split("\n") if l.strip() and not l.startswith("=")]
                        if lines:
                            self.ui.write_log(f"SYS: {lines[0][:70]}")
                    except Exception as e:
                        print(f"[Worker] Full cycle error: {e}")

            except Exception as e:
                self.ui.write_log(f"SYS: Worker loop error: {str(e)[:60]}")
                await asyncio.sleep(30)

    async def _screen_awareness_loop(self):
        """Passive screen context — only used when user asks for help."""
        while True:
            await asyncio.sleep(60)
            if self._shutdown_requested.is_set():
                return
            try:
                self._screen_awareness.should_read_screen()
            except Exception:
                pass
    async def run(self):
        api_key = _get_api_key()
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1beta"}
        )
        self._genai_client = client
        live_model = await asyncio.to_thread(pick_live_model, client, API_CONFIG_PATH)
        live_model_id = live_model.removeprefix("models/")
        self.ui.write_log(f"SYS: Gemini Live model selected: {live_model_id}")
        print(f"[Assistant] Model: {live_model_id}", flush=True)

        start_time = time.time()
        while True:
            try:
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=live_model_id, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self._loop.set_exception_handler(_async_exception_hook)
                    self._tg            = tg
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=200)
                    self._turn_done_event = asyncio.Event()
                    self._conv_memory.start_session()

                    self._reconnect_attempt = 0
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: Assistant online.")
                    print("[Assistant] ✅ Gemini Live session connected!", flush=True)
                    try:
                        jarvis_status.write_status({
                            "state": "online",
                            "voice": self._get_current_voice(),
                            "pid": os.getpid(),
                        })
                    except Exception:
                        pass

                    tg.create_task(self._safe_task("send_realtime", self._send_realtime()))
                    tg.create_task(self._safe_task("listen_audio", self._listen_audio()))
                    tg.create_task(self._safe_task("receive_audio", self._receive_audio()))
                    tg.create_task(self._safe_task("play_audio", self._play_audio()))
                    tg.create_task(self._safe_task("announce_startup", self._announce_startup()))
                    tg.create_task(self._safe_task("keepalive_ping", self._keepalive_ping()))
                    tg.create_task(self._safe_task("periodic_screen_watch", self._periodic_screen_watch()))
                    tg.create_task(self._safe_task("periodic_vision", self._periodic_vision()))
                    tg.create_task(self._safe_task("autonomous_monitor", self._autonomous_monitor()))
                    tg.create_task(self._safe_task("mood_checkin_loop", self._mood_checkin_loop()))
                    tg.create_task(self._safe_task("screen_awareness_loop", self._screen_awareness_loop()))
                    tg.create_task(self._safe_task("money_making_loop", self._money_making_loop()))

            except Exception as e:
                actual = e
                if isinstance(e, ExceptionGroup) and len(e.exceptions) == 1:
                    actual = e.exceptions[0]

                error_msg = str(actual)
                diagnosis = report_error(error_msg, model=live_model_id)
                self._conv_memory.end_session()

                if self._shutdown_requested.is_set():
                    return

                print(f"[Assistant] ⚠️ Session error: {error_msg[:200]}", flush=True)

                if _is_normal_live_close_error(actual) or (
                    genai is not None and isinstance(actual, genai.errors.APIError) and "1000" in str(actual)
                ):
                    self._conv_memory.end_session()
                    self._reconnect_attempt = 0
                    try:
                        jarvis_status.write_status({"state": "offline"})
                    except Exception:
                        pass
                elif "content_type_audio" in error_msg.lower() or "response_modalities" in error_msg.lower():
                    self._reconnect_attempt += 1
                    new_model = await asyncio.to_thread(
                        get_fallback_model, self._genai_client, live_model, API_CONFIG_PATH
                    )
                    if new_model:
                        live_model = new_model
                        live_model_id = live_model.removeprefix("models/")
                        self._reconnect_attempt = 0
                    await self._wait_before_reconnect(3.0)
                elif _is_transient_live_connection_error(actual) or (
                    isinstance(actual, Exception)
                    and any(code in error_msg for code in ("1006", "1007", "1011", "1012", "1014"))
                ):
                    if "session duration limit" in error_msg.lower():
                        self._reconnect_attempt = 0
                    else:
                        self._reconnect_attempt += 1
                    delay = _live_reconnect_delay(self._reconnect_attempt)
                    if should_change_model(self._reconnect_attempt):
                        new_model = await asyncio.to_thread(
                            get_fallback_model, self._genai_client, live_model, API_CONFIG_PATH
                        )
                        if new_model:
                            live_model = new_model
                            live_model_id = live_model.removeprefix("models/")
                            self._reconnect_attempt = 0
                    await self._wait_before_reconnect(delay)
                elif _is_unsupported_voice_error(actual) and self.voice_name != DEFAULT_VOICE_NAME:
                    old_voice = self.voice_name
                    self.voice_name = DEFAULT_VOICE_NAME
                    self._reconnect_attempt = 0
                    try:
                        jarvis_status.write_status({"state": "voice_fallback", "voice": DEFAULT_VOICE_NAME})
                    except Exception:
                        pass
                elif _is_transient_live_connection_error(actual):
                    self._reconnect_attempt += 1
                    delay = _live_reconnect_delay(self._reconnect_attempt)
                    await self._wait_before_reconnect(delay)
                else:
                    self._reconnect_attempt += 1
                    if self._reconnect_attempt > 10:
                        await self._wait_before_reconnect(15.0)
                        self._reconnect_attempt = 5
                    else:
                        delay = min(1.0 * self._reconnect_attempt, 10.0)
                        await self._wait_before_reconnect(delay)

def main():
    print("[Assistant] main() called", flush=True)
    from pathlib import Path as _P
    try:
        (_P(__file__).resolve().parent / ".jarvis" / ".stop").unlink(missing_ok=True)
    except Exception:
        pass
    if not wait_for_startup_claps():
        return
    os.environ.setdefault("JARVIS_AUTO_START", "1")
    print("[Assistant] ⚡ Powering up the interface...", flush=True)
    try:
        ui = JarvisUI("face.png")
    except Exception as exc:
        print(f"[Assistant] ❌ Interface startup failed: {exc}", flush=True)
        traceback.print_exc()
        return

    def runner():
        ui.wait_for_api_key()
        voice_name = _load_voice_name()
        max_restarts = 50
        restart_count = 0
        immediate_fail_count = 0
        
        while restart_count < max_restarts:
            try:
                jarvis = JarvisLive(ui, voice_name)
                ui.on_quit_requested = jarvis.request_shutdown
                ui.on_voice_change = jarvis.update_voice
                
                def _on_tts_change(provider, api_key, voice_id):
                    if provider == "gemini":
                        jarvis._tts_engine = None
                        jarvis._ext_tts_provider = ""
                        jarvis._ext_tts_voice_id = ""
                        jarvis._ext_tts_api_key = ""
                        jarvis.update_voice(voice_id)
                    else:
                        jarvis._ext_tts_provider = provider
                        jarvis._ext_tts_voice_id = voice_id
                        jarvis._ext_tts_api_key = api_key
                        try:
                            jarvis._tts_engine = _lazy("tts_engine")(
                                provider=provider,
                                api_key=api_key,
                                voice_id=voice_id,
                                on_speaking_start=lambda: jarvis.set_speaking(True),
                                on_speaking_stop=lambda: jarvis.set_speaking(False),
                            )
                            jarvis.ui.write_log(f"SYS: TTS engine ready: {provider} / {voice_id}")
                            jarvis.ui.write_log("SYS: Gemini audio muted - using external TTS")
                        except Exception as e:
                            jarvis.ui.write_log(f"SYS: TTS engine error: {e}")
                        if jarvis.session and jarvis._loop:
                            try:
                                asyncio.run_coroutine_threadsafe(jarvis.session.close(), jarvis._loop)
                            except Exception as e:
                                print(f"[Assistant] Could not close session: {e}")
                
                ui.on_tts_provider_change = _on_tts_change
                start_time = time.time()
                asyncio.run(jarvis.run())
                elapsed = time.time() - start_time
                if elapsed < 5.0:
                    immediate_fail_count += 1
                    if immediate_fail_count >= 3:
                        print("[Assistant] ❌ JARVIS crashed immediately 3 times. Stopping.", flush=True)
                        try:
                            ui.write_log("SYS: Failed to start 3 times. Check API key and network.")
                        except Exception:
                            pass
                        # Tell the watchdog this was a hard failure, not user intent.
                        # Prevent infinite rapid restarts.
                        try:
                            (_P(__file__).resolve().parent / ".jarvis" / ".stop").write_text(
                                "startup_failure", encoding="utf-8")
                        except Exception:
                            pass
                        break
                else:
                    immediate_fail_count = 0
                break
                
            except KeyboardInterrupt:
                print("\n Shutting down...", flush=True)
                break
            except Exception as exc:
                restart_count += 1
                message = f"Runner error (attempt {restart_count}): {str(exc)[:180]}"
                print(f"[Assistant] {message}", flush=True)
                try:
                    ui.write_log(f"SYS: Restarting... ({restart_count}/{max_restarts})")
                    ui.set_state("LISTENING")
                except Exception:
                    pass
                import time as _time
                _time.sleep(min(3 * restart_count, 30))
        
        if restart_count >= max_restarts:
            print("[Assistant] Max restarts reached. Exiting.", flush=True)
            try:
                ui.write_log("SYS: Too many crashes. Stopped.")
            except Exception:
                pass
            try:
                (_P(__file__).resolve().parent / ".jarvis" / ".stop").write_text(
                    "max_restarts", encoding="utf-8")
            except Exception:
                pass

    def _start_api_server():
        try:
            import uvicorn
            from api.server import app
            uvicorn.run(app, host="127.0.0.1", port=8081, log_level="error")
        except ImportError:
            print("[Assistant] ⚠️ API server skipped: uvicorn or api.server not installed", flush=True)
        except OSError as e:
            print(f"[Assistant] ⚠️ API server port error: {e}", flush=True)
        except Exception as e:
            print(f"[Assistant] ⚠️ API server failed: {type(e).__name__}: {e}", flush=True)
    threading.Thread(target=_start_api_server, daemon=True).start()

    threading.Thread(target=runner, daemon=True).start()
    print("[Assistant] ✅ Interface ready.", flush=True)
    ui.root.mainloop()
    print("[Assistant] Interface closed.", flush=True)

def cli_main():
    """Canonical console entry point installed as the `jarvis` command."""
    os.environ["JARVIS_CLI"] = "1"
    return main()


if __name__ == "__main__":
    main()

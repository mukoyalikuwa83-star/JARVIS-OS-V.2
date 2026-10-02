"""Headless AI health check for JARVIS.

Answers the question "does the AI actually work?" without a display,
microphone, or Qt UI. Run it with the project virtualenv interpreter:

    .venv/Scripts/python.exe scripts/ai_smoke.py

Stages:
  1. config   — .env loads and GEMINI_API_KEY is usable
  2. tools    — every declared tool maps to a real handler; every module
                imported by the dispatcher imports cleanly
  3. schema   — core.tool_registry converts into a valid Gemini tool schema
  4. config   — JarvisLive builds a live connect config (prompt, tools, voice)
  5. live     — a real Gemini Live session: greeting turn, tool-call
                round-trip through the real dispatcher, spoken reply

Exit code 0 means every stage passed. Use --no-live to skip the network
stages (3-5 still need no network; only stage 5 does).
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import importlib
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

try:  # Windows consoles are often cp1252; keep output printable either way.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_RESULTS: list[tuple[str, bool, str]] = []
_START = time.monotonic()


def record(stage: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((stage, ok, detail))
    mark = "PASS" if ok else "FAIL"
    elapsed = time.monotonic() - _START
    print(f"[{mark}] {stage} (+{elapsed:.1f}s){(' — ' + detail) if detail else ''}", flush=True)


def _fail(stage: str, detail: str) -> None:
    record(stage, False, detail)


# ---------------------------------------------------------------------------
# stub UI — JarvisLive expects a JarvisUI-like object
# ---------------------------------------------------------------------------
class StubUI:
    """Minimal stand-in for JarvisUI so JarvisLive can be constructed headlessly."""

    def __init__(self) -> None:
        self.muted = False
        self.operational_ready = True
        self.on_text_command = None
        self.current_file = None
        self.log: list[str] = []
        self.subtitles: list[str] = []
        self.states: list[str] = []

    def write_log(self, message) -> None:
        self.log.append(str(message))

    def set_state(self, state) -> None:
        self.states.append(str(state))

    def set_mic_state(self, *_a, **_k) -> None:
        pass

    def show_subtitle(self, text) -> None:
        self.subtitles.append(str(text))

    def clear_subtitle(self) -> None:
        pass

    def handle_ui_command(self, *_a, **_k):
        return None

    def set_theme(self, *_a, **_k) -> None:
        pass

    def set_graphics_quality(self, *_a, **_k) -> None:
        pass

    def sync_voice_display(self, *_a, **_k) -> None:
        pass


# ---------------------------------------------------------------------------
# stage 1 — credentials
# ---------------------------------------------------------------------------
def check_config() -> bool:
    try:
        import main as jarvis_main  # noqa: F401  (module import applies _load_dotenv)
    except Exception as exc:
        _fail("config", f"main.py failed to import: {type(exc).__name__}: {exc}")
        return False

    try:
        key = jarvis_main._get_api_key()
    except Exception as exc:
        _fail("config", str(exc))
        return False

    if not key.strip():
        _fail("config", "GEMINI_API_KEY is empty")
        return False

    record("config", True, f"GEMINI_API_KEY loaded from .env ({len(key)} chars, prefix {key[:4]!r})")
    return True


# ---------------------------------------------------------------------------
# stage 2 — tool wiring
# ---------------------------------------------------------------------------
def _execute_tool_node() -> ast.AsyncFunctionDef | None:
    src = (BASE_DIR / "main.py").read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_execute_tool":
            return node
    return None


def _string_constants(node: ast.AST) -> list[str]:
    values: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        values.append(node.value)
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for element in node.elts:
            values.extend(_string_constants(element))
    return values


def dispatched_tool_names() -> set[str]:
    """Tool names the dispatcher compares against, e.g. ``name == "open_app"``."""
    func = _execute_tool_node()
    names: set[str] = set()
    if func is None:
        return names
    for sub in ast.walk(func):
        if not isinstance(sub, ast.Compare):
            continue
        if not (isinstance(sub.left, ast.Name) and sub.left.id == "name"):
            continue
        for comparator in sub.comparators:
            names.update(_string_constants(comparator))
    return names


def dispatcher_imports() -> list[tuple[str, tuple[str, ...]]]:
    """``(module, (attr, ...))`` pairs imported inside the dispatcher."""
    func = _execute_tool_node()
    targets: list[tuple[str, tuple[str, ...]]] = []
    if func is None:
        return targets
    for sub in ast.walk(func):
        if isinstance(sub, ast.ImportFrom) and sub.module and sub.level == 0:
            if sub.module.split(".")[0] in {"actions", "agent", "core", "memory", "actions_shared"}:
                targets.append((sub.module, tuple(alias.name for alias in sub.names)))
    return targets


def lazy_names_used() -> list[str]:
    func = _execute_tool_node()
    names: list[str] = []
    if func is None:
        return names
    for sub in ast.walk(func):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "_lazy":
            for arg in sub.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.append(arg.value)
    return names


def check_tools() -> bool:
    from core.tool_registry import TOOL_DECLARATIONS

    declared = [entry["name"] for entry in TOOL_DECLARATIONS]
    duplicates = sorted({name for name in declared if declared.count(name) > 1})
    dispatched = dispatched_tool_names()

    unreachable = [name for name in declared if name not in dispatched]
    orphans = sorted(name for name in dispatched if name not in declared)
    ok = not duplicates and not unreachable
    detail = f"{len(declared)} tools declared, {len(dispatched)} handled in dispatcher"
    if duplicates:
        detail += f"; duplicate declarations: {', '.join(duplicates)}"
    if unreachable:
        detail += f"; NO HANDLER: {', '.join(unreachable)}"
    record("tools.wiring", ok, detail)
    if orphans:
        print(f"    note: handled but not declared: {', '.join(orphans)}")

    imports = sorted(set(dispatcher_imports()))
    broken: list[str] = []
    for module, attrs in imports:
        try:
            mod = importlib.import_module(module)
        except Exception as exc:
            broken.append(f"{module} ({type(exc).__name__}: {exc})")
            continue
        for attr in attrs:
            if attr != "*" and not hasattr(mod, attr):
                broken.append(f"{module}.{attr} missing")
    record("tools.modules", not broken, "; ".join(broken) if broken else
           f"all {len(imports)} dispatcher imports resolve")

    from actions import lazy_loader

    lazy_used = sorted(set(lazy_names_used()))
    unresolved = [name for name in lazy_used if lazy_loader.get_handler(name) is None]
    record(
        "tools.lazy",
        not unresolved,
        ("; ".join(unresolved) if unresolved else
         f"lazy handlers resolve: {', '.join(lazy_used)}" if lazy_used else
         "dispatcher uses no lazy lookups (every tool imports its module directly)"),
    )

    return ok and not broken and not unresolved


# ---------------------------------------------------------------------------
# stage 3 — API schema
# ---------------------------------------------------------------------------
def check_schema() -> bool:
    from google.genai import types

    from core.tool_registry import TOOL_DECLARATIONS

    try:
        tool = types.Tool(function_declarations=TOOL_DECLARATIONS)
        names = [fd.name for fd in tool.function_declarations]
    except Exception as exc:
        _fail("tools.schema", f"{type(exc).__name__}: {exc}")
        return False

    blank = [fd.name for fd in tool.function_declarations if not (fd.description or "").strip()]
    record("tools.schema", not blank,
           f"{len(names)} declarations accepted by google-genai"
           + (f"; missing descriptions: {', '.join(blank)}" if blank else ""))
    return not blank


# ---------------------------------------------------------------------------
# stage 4 — live connect config
# ---------------------------------------------------------------------------
def check_connect_config(jarvis, jarvis_main) -> bool:
    try:
        config = jarvis._build_config()
    except Exception as exc:
        _fail("live.config", f"{type(exc).__name__}: {exc}")
        return False

    prompt = config.system_instruction or ""
    problems = []
    if len(prompt) < 200:
        problems.append(f"system prompt suspiciously short ({len(prompt)} chars)")
    tools = (config.tools or [{}])[0]
    declarations = getattr(tools, "function_declarations", None) or []
    if not declarations:
        problems.append("no function declarations attached")
    if config.response_modalities != ["AUDIO"]:
        problems.append(f"response_modalities={config.response_modalities!r}")
    try:
        voice = config.speech_config.voice_config.prebuilt_voice_config.voice_name
    except Exception:
        voice = None
    if not voice:
        problems.append("no voice configured")

    record("live.config", not problems,
           f"prompt {len(prompt)} chars, {len(declarations)} tools, voice={voice}"
           + ("; " + "; ".join(problems) if problems else ""))
    return not problems


# ---------------------------------------------------------------------------
# stage 5 — real live session
# ---------------------------------------------------------------------------
TOOL_PROMPT = (
    "Use the system_info tool with action 'time' to get the exact current time, "
    "then tell me the time in one short spoken sentence."
)


async def live_session_probe(
    jarvis, jarvis_main, model_id: str, timeout: float, verbose: bool = False
) -> tuple[bool, str]:
    from google import genai

    api_key = jarvis_main._get_api_key()
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    config = jarvis._build_config()

    said: list[str] = []
    tool_names: list[str] = []
    tool_results: list[str] = []
    audio_bytes = 0
    phase = 1
    tool_prompt_sent_at = 0.0
    events: list[str] = []
    deadline = time.monotonic() + timeout

    async with client.aio.live.connect(model=model_id, config=config) as session:
        print(f"    connected to {model_id}", flush=True)
        await session.send_client_content(
            turns={"parts": [{"text": "Greet me in under ten words."}]},
            turn_complete=True,
        )

        # google-genai ends a receive() generator between turns; the real receive
        # loop in main.py re-enters it inside `while True`, so mirror that here.
        idle_rounds = 0
        while time.monotonic() < deadline:
            produced = False
            async for response in session.receive():
                produced = True
                audio = jarvis_main._live_response_audio_bytes(response)
                if audio:
                    audio_bytes += len(audio)

                sc = response.server_content
                if sc and sc.output_transcription and sc.output_transcription.text:
                    said.append(sc.output_transcription.text.strip())
                if response.tool_call:
                    fn_responses = []
                    for fc in response.tool_call.function_calls:
                        tool_names.append(fc.name)
                        print(f"    tool call -> {fc.name} {dict(fc.args or {})}", flush=True)
                        fr = await jarvis._execute_tool(fc)
                        payload = getattr(fr, "response", None) or {}
                        tool_results.append(str(payload.get("result", payload))[:200])
                        fn_responses.append(fr)
                    if fn_responses:
                        await session.send_tool_response(function_responses=fn_responses)

                if verbose:
                    events.append(
                        f"audio={len(audio)} tool_call={bool(response.tool_call)} "
                        f"complete={bool(sc and sc.turn_complete)}"
                    )

                if sc and sc.turn_complete:
                    recent_send = time.monotonic() - tool_prompt_sent_at < 1.0
                    if phase == 1:
                        print(f"    turn 1 complete ({audio_bytes} audio bytes)", flush=True)
                        phase = 2
                        tool_prompt_sent_at = time.monotonic()
                        await session.send_client_content(
                            turns={"parts": [{"text": TOOL_PROMPT}]}, turn_complete=True
                        )
                    elif tool_names and not recent_send:
                        print(f"    turn 2 complete ({audio_bytes} audio bytes)", flush=True)
                        return _summarize(True, said, tool_names, tool_results, audio_bytes, events,
                                          verbose=verbose)
            if not produced:
                idle_rounds += 1
                if idle_rounds > 60:
                    break
                await asyncio.sleep(0.25)
            else:
                idle_rounds = 0

    ok = bool(tool_names)
    return _summarize(ok, said, tool_names, tool_results, audio_bytes, events, verbose=verbose)


def _summarize(ok, said, tool_names, tool_results, audio_bytes, events, verbose=False) -> tuple[bool, str]:
    transcript = " ".join(t for t in said if t)
    summary = (
        f"transcript={transcript[:200]!r} | audio={audio_bytes} bytes | "
        f"tools={tool_names or 'none'}"
    )
    if tool_results:
        summary += f" | tool_result={tool_results[0][:120]!r}"
    if verbose and events:
        print("    events: " + " | ".join(events[:25]), flush=True)
    return bool(ok), summary


def check_live(jarvis, jarvis_main, model_override: str | None, timeout: float, verbose: bool = False) -> bool:
    from core.live_model import BLOCKED_MODELS, configured_live_model

    model_id = model_override or configured_live_model(jarvis_main.API_CONFIG_PATH)
    if model_id in BLOCKED_MODELS:
        print(f"    configured model {model_id} is blocklisted; using the pinned default", flush=True)
        model_id = jarvis_main.LIVE_MODEL
    model_id = model_id.removeprefix("models/")
    try:
        ok, summary = asyncio.run(
            asyncio.wait_for(
                live_session_probe(jarvis, jarvis_main, model_id, timeout, verbose=verbose),
                timeout=timeout + 10.0,
            )
        )
    except asyncio.TimeoutError:
        _fail("live.session", f"no completed turn within {timeout:.0f}s")
        return False
    except Exception as exc:
        _fail("live.session", f"{type(exc).__name__}: {str(exc)[:300]}")
        return False

    record("live.session", ok, summary)
    if not ok:
        print("    note: the model replied but never called a tool; check the tool schema/prompt.", flush=True)
    return ok


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Headless AI health check for JARVIS")
    parser.add_argument("--no-live", action="store_true", help="skip the real Gemini Live session")
    parser.add_argument("--model", default=None, help="override the live model id")
    parser.add_argument("--timeout", type=float, default=90.0, help="live session timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="print per-message live session events")
    args = parser.parse_args()

    started = time.time()
    print("JARVIS AI smoke test", flush=True)
    print(f"python {sys.version.split()[0]} | root {BASE_DIR}", flush=True)

    if not check_config():
        return 1

    jarvis_main = sys.modules["main"]
    ui = StubUI()
    try:
        jarvis = jarvis_main.JarvisLive(ui, jarvis_main._load_voice_name())
        record("runtime.init", True, f"JarvisLive constructed (voice={jarvis.voice_name})")
    except Exception as exc:
        _fail("runtime.init", f"{type(exc).__name__}: {exc}")
        jarvis = None

    check_tools()
    check_schema()

    if jarvis is not None:
        check_connect_config(jarvis, jarvis_main)
        if not args.no_live:
            check_live(jarvis, jarvis_main, args.model, args.timeout, verbose=args.verbose)

    passed = sum(1 for _s, ok, _d in _RESULTS if ok)
    failed = [stage for stage, ok, _d in _RESULTS if not ok]
    print(f"\n{passed}/{len(_RESULTS)} checks passed in {time.time() - started:.1f}s", flush=True)
    if failed:
        print("FAILED: " + ", ".join(failed), flush=True)
        return 1
    print("AI path OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

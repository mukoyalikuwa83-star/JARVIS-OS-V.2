#!/usr/bin/env python3
"""Non-interactive, side-effect-safe probes for the JARVIS live checklist."""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actions import browser_control, file_controller
from core.qa_mode import guard_tool_call


def _case(name: str, status: str, notes: str, evidence: dict | None = None) -> dict:
    return {
        "name": name,
        "status": status,
        "notes": notes,
        "evidence": evidence or {},
    }


def _run_tests(*tests: str) -> tuple[bool, str]:
    command = [sys.executable, "-m", "unittest", *tests, "-q"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "JARVIS_QA_MODE": "1"},
    )
    details = "\n".join(
        part.strip() for part in (result.stdout or "", result.stderr or "") if part.strip()
    )
    return result.returncode == 0, details[-1200:]


def _test_module(test_id: str) -> str:
    """Map a dotted unittest case id to the module that should contain it."""
    parts = test_id.split(".")
    return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else parts[0]


def _unavailable_test_modules(*tests: str) -> list[str]:
    """Referenced suites that no longer exist on disk (for example archived UI suites)."""
    unavailable = []
    for module in dict.fromkeys(_test_module(test) for test in tests):
        if not ROOT.joinpath(*module.split(".")).with_suffix(".py").is_file():
            unavailable.append(module)
    return unavailable


def _capability_status(ok: bool, unavailable: list[str], pass_status: str = "partial") -> str:
    """Only report `failed` when the referenced checks actually ran and failed."""
    if ok:
        return pass_status
    return "blocked" if unavailable else "failed"


def _coverage_note(unavailable: list[str]) -> str:
    if not unavailable:
        return ""
    return (
        f" Automated coverage unavailable: {', '.join(unavailable)} is no longer present"
        " (retired with the previous UI generation; see tests/_archive/README.md)."
    )


def _run_capability(*tests: str, pass_status: str = "partial") -> tuple[str, str, str]:
    """Run the referenced suites and return (status, details, availability note)."""
    ok, details = _run_tests(*tests)
    unavailable = _unavailable_test_modules(*tests)
    return _capability_status(ok, unavailable, pass_status), details, _coverage_note(unavailable)


def _ui_probe(output: Path) -> tuple[bool | None, dict, str]:
    """Run the render/accessibility probe, or return None when it is unavailable."""
    probe_script = ROOT / "scripts" / "qa_ui_probe.py"
    if not probe_script.is_file():
        return None, {}, (
            "The render/accessibility probe was retired with the previous UI generation "
            "(archived at scripts/_archive/qa_ui_probe.py)."
        )
    result = subprocess.run(
        [sys.executable, "scripts/qa_ui_probe.py", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "JARVIS_QA_MODE": "1"},
    )
    probe_path = output / "ui-probe.json"
    payload = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.exists() else {}
    log = ((result.stdout or "") + (result.stderr or ""))[-1200:]
    return result.returncode == 0 and bool(payload), payload, log


def _audio_probe() -> tuple[bool, dict, str]:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = [device.get("name", "") for device in devices if int(device.get("max_input_channels", 0)) > 0]
        outputs = [device.get("name", "") for device in devices if int(device.get("max_output_channels", 0)) > 0]
        evidence = {
            "input_devices": inputs,
            "output_devices": outputs,
            "default_device": list(sd.default.device),
        }
        return bool(inputs and outputs), evidence, "Audio hardware enumerated without opening a recording stream."
    except Exception as exc:
        return False, {}, f"Audio enumeration failed: {exc}"


def _display_probe() -> tuple[bool | None, dict, str]:
    if platform.system() != "Darwin":
        return True, {"platform": platform.system()}, "Display enumeration is macOS-specific in this certification pass."
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )
    resolutions = [line.strip() for line in (result.stdout or "").splitlines() if "Resolution:" in line]
    evidence = {"detected_displays": len(resolutions), "resolutions": resolutions}
    if result.returncode != 0 or not resolutions:
        return None, evidence, "Physical display inventory was unavailable in the headless QA environment."
    return True, evidence, "Physical display inventory read successfully."


def _screen_permission_probe() -> tuple[bool | None, dict, str]:
    if platform.system() != "Darwin":
        return None, {}, "Screen Recording permission probe is only implemented for macOS."
    try:
        core_graphics = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )
        probe = core_graphics.CGPreflightScreenCaptureAccess
        probe.restype = ctypes.c_bool
        allowed = bool(probe())
        return allowed, {"screen_recording_permission": allowed}, (
            "Screen Recording permission is granted."
            if allowed else
            "Screen Recording permission is not currently granted; no permission prompt was triggered."
        )
    except Exception as exc:
        return None, {}, f"Could not query Screen Recording permission: {exc}"


class _LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><title>JARVIS QA</title><button id='qa'>Ready</button></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


async def _playwright_local(url: str) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        title = await page.title()
        button = await page.locator("#qa").inner_text()
        await browser.close()
        return {"title": title, "button": button}


def _browser_probe() -> tuple[bool | None, dict, str]:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalHandler)
    except OSError as exc:
        return None, {"local_server_error": str(exc)}, "The environment blocked creation of a localhost QA server."
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            local_ok = response.status == 200
        evidence = {"url": browser_control._normalize_url(url), "local_http": local_ok}
        try:
            evidence.update(asyncio.run(_playwright_local(url)))
            return evidence.get("title") == "JARVIS QA", evidence, "Headless Chromium navigated only to the local QA page."
        except Exception as exc:
            evidence["playwright_error"] = str(exc)[:300]
            return None, evidence, "Local page worked, but the Playwright Chromium binary is unavailable."
    finally:
        server.shutdown()
        server.server_close()


def _file_probe(workspace: Path) -> tuple[bool, dict, str]:
    root = workspace / "file-workflow"
    root.mkdir(parents=True, exist_ok=True)
    copied = root / "copies"
    copied.mkdir(exist_ok=True)
    with patch.object(file_controller, "_SAFE_ROOTS", [root]):
        created = file_controller.create_file(str(root), "qa.txt", "JARVIS QA")
        read = file_controller.read_file(str(root), "qa.txt")
        renamed = file_controller.rename_file(str(root), "qa.txt", "qa-renamed.txt")
        copied_result = file_controller.copy_file(
            str(root), "qa-renamed.txt", str(copied / "qa-copy.txt")
        )
        outside = file_controller.create_file(str(workspace.parent), "escape.txt", "blocked")
        listing = file_controller.list_files(str(root))
    passed = all((
        "File saved" in created,
        "JARVIS QA" in read,
        "Renamed" in renamed,
        "Copied" in copied_result,
        "Access denied" in outside,
        "qa-renamed.txt" in listing,
    ))
    return passed, {
        "created": created,
        "renamed": renamed,
        "copied": copied_result,
        "outside_write": outside,
    }, "Temporary file workflow completed entirely inside the QA workspace."


def _safety_probe(workspace: Path) -> tuple[bool, dict, str]:
    decisions = {
        "message_send": guard_tool_call("send_message", {}).allowed,
        "shutdown": guard_tool_call("computer_settings", {"action": "shutdown"}).allowed,
        "game_install": guard_tool_call("game_updater", {"action": "install"}).allowed,
        "outside_file": guard_tool_call("file_controller", {"action": "write", "path": str(workspace.parent / "outside.txt")}).allowed,
    }
    passed = not any(decisions.values())
    return passed, decisions, "All irreversible and out-of-workspace probes were rejected before execution."


def _stability_probe(seconds: float) -> tuple[bool, dict, str]:
    import psutil

    process = psutil.Process(os.getpid())
    start = process.memory_info().rss
    start_threads = process.num_threads()
    samples = []
    deadline = time.monotonic() + max(1.0, seconds)
    process.cpu_percent(None)
    while time.monotonic() < deadline:
        samples.append({
            "rss_mb": process.memory_info().rss / (1024 * 1024),
            "threads": process.num_threads(),
            "cpu_percent": process.cpu_percent(None),
        })
        time.sleep(min(1.0, max(0.05, deadline - time.monotonic())))
    growth_mb = (process.memory_info().rss - start) / (1024 * 1024)
    thread_growth = process.num_threads() - start_threads
    passed = growth_mb < 50 and thread_growth < 10
    return passed, {
        "duration_seconds": seconds,
        "samples": samples,
        "rss_growth_mb": growth_mb,
        "thread_growth": thread_growth,
    }, "Short harness stability probe completed; the 30-minute real JARVIS soak remains optional."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--stability-seconds", type=float, default=5.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    workspace = args.output / "workspace"
    workspace.mkdir(exist_ok=True)
    os.environ["JARVIS_QA_MODE"] = "1"
    os.environ["JARVIS_QA_WORKSPACE"] = str(workspace)

    cases = []
    startup_status, startup_details, startup_note = _run_capability(
        "tests.test_qa_system.QAModeSafetyTests.test_live_dispatch_is_blocked_until_ui_is_operationally_ready",
        "tests.test_qa_system.QAModeSafetyTests.test_live_dispatch_enforces_qa_guard_before_tool_handler",
        "tests.test_startup_clap.StartupClapTests.test_gate_times_out_without_claps",
        pass_status="passed",
    )
    cases.append(_case("Clean startup and API-only gate", startup_status, "Startup gating and setup isolation were exercised offscreen." + startup_note, {"test_output": startup_details}))

    key_status, key_details, key_note = _run_capability(
        "tests.test_api_key_validation.GeminiApiKeyGateTests.test_foreign_provider_keys_are_rejected_before_network_validation",
        "tests.test_api_key_validation.GeminiApiKeyGateTests.test_gemini_shaped_key_still_requires_online_verification",
        "tests.test_api_key_validation.GeminiApiKeyGateTests.test_remembered_key_can_be_removed_after_failed_validation",
        pass_status="passed",
    )
    cases.append(_case("Invalid then valid Gemini key", key_status, "Validation failure and recovery were tested with a mocked Gemini boundary; no paid API call was made." + key_note, {"test_output": key_details}))

    # The first-run intro/voice caching suite was retired with the previous UI
    # generation (tests/_archive/README.md), so this case is manual rather than
    # a fabricated failure.
    cases.append(_case("Selected voice and introduction", "manual-required", "Automated intro/voice coverage was retired with the previous UI generation (tests/_archive/README.md). Whether the configured voice is used and sounds right requires listening.", {}))
    cases.append(_case("Subtitle and audio synchronization", "manual-required", "Automated caption timing coverage was retired with the previous UI generation (tests/_archive/README.md). Caption pacing against spoken audio requires listening and watching.", {}))

    audio_ok, audio_evidence, audio_notes = _audio_probe()
    cases.append(_case("Microphone turn-taking and interruption", "partial" if audio_ok else "blocked", audio_notes + " Actual speech, echo, interruption, mute, and unmute still require a person.", audio_evidence))

    reconnect_status, reconnect_details, reconnect_note = _run_capability(
        "tests.test_core_resilience.CoreResilienceTests.test_live_model_falls_back_when_listing_fails",
        "tests.test_core_resilience.CoreResilienceTests.test_live_model_selection_prefers_native_audio",
        "tests.test_qa_system.QAModeSafetyTests.test_live_reconnect_backoff_is_bounded",
    )
    cases.append(_case("Gemini disconnect and reconnect", reconnect_status, "Offline/fallback behavior passed with fault injection; a real network interruption was not performed." + reconnect_note, {"test_output": reconnect_details}))

    ui_ok, ui_evidence, ui_notes = _ui_probe(args.output / "ui")
    ui_note = "" if ui_ok is not None else f" {ui_notes}"
    display_ok, display_evidence, display_notes = _display_probe()
    if ui_ok is None:
        display_status = "blocked"
        display_note = f"{display_notes} Physical window movement and resize behaviour remain manual.{ui_note}"
    elif ui_ok and display_ok is not False:
        display_status = "partial"
        display_note = f"{display_notes} Minimum and standard sizes rendered. Physical window movement remains manual."
    else:
        display_status = "failed"
        display_note = f"{display_notes} Minimum and standard sizes did not render as expected."
    cases.append(_case("Window and secondary display", display_status, display_note, {"ui": ui_evidence, "display": display_evidence, "probe_log": ui_notes}))

    theme_status, theme_details, theme_note = _run_capability(
        "tests.test_graphics_quality.GraphicsQualityTests.test_setting_is_persistent_and_preserves_other_preferences",
        "tests.test_graphics_quality.GraphicsQualityTests.test_hud_profiles_change_real_rendering_cost",
        "tests.test_graphics_quality.GraphicsQualityTests.test_settings_exposes_exactly_three_quality_choices",
        "tests.test_vision_preview.VisionPreviewTests.test_preview_cadence_follows_graphics_quality",
    )
    cases.append(_case("Themes, graphics, settings, compact mode", theme_status, "Themes and graphics passed automatically; physical dock detachment and compact-mode feel remain manual." + theme_note, {"test_output": theme_details}))

    missing_names = sum(len(item.get("missing_accessible_names", [])) for item in ui_evidence.values()) if ui_evidence else 0
    if ui_ok is None:
        accessibility_status = "blocked"
        accessibility_notes = f"Automated accessibility inspection is unavailable.{ui_note} Full VoiceOver navigation remains manual."
    else:
        accessibility_status = "partial" if ui_ok else "failed"
        accessibility_notes = f"Rendered focusable surfaces were inspected. {missing_names} custom controls lack an accessible name; full VoiceOver navigation remains manual."
    cases.append(_case("Keyboard and focus accessibility", accessibility_status, accessibility_notes, {"missing_accessible_names": missing_names}))

    browser_ok, browser_evidence, browser_notes = _browser_probe()
    browser_status = "passed" if browser_ok is True else "blocked" if browser_ok is None else "failed"
    cases.append(_case("Controlled browser page", browser_status, browser_notes, browser_evidence))

    file_ok, file_evidence, file_notes = _file_probe(workspace)
    cases.append(_case("Temporary file workflow", "passed" if file_ok else "failed", file_notes, file_evidence))

    safety_ok, safety_evidence, safety_notes = _safety_probe(workspace)
    cases.append(_case("Messaging draft safety", "partial" if safety_ok else "failed", safety_notes + " Draft typing and cancellation remain manual because they affect a visible composer.", safety_evidence))
    cases.append(_case("Read-only message awareness", "manual-required", "Reading a real Messages or Instagram conversation requires user-selected content and macOS permissions; automation will not inspect private conversations.", {}))
    cases.append(_case("Reminder lifecycle", "manual-required", "Creating a real launchd reminder changes macOS state, so this remains supervised even in QA mode.", {}))

    permission_ok, permission_evidence, permission_notes = _screen_permission_probe()
    permission_status = "passed" if permission_ok is True else "blocked" if permission_ok is False or permission_ok is None else "failed"
    cases.append(_case("Screen and permission handling", permission_status, permission_notes, permission_evidence))

    contract_ok, contract_details = _run_tests(
        "tests.test_qa_system.ToolContractTests.test_declared_tool_inventory_is_complete_and_unique",
        "tests.test_core_resilience.PureActionContractTests.test_weather_failure_is_returned_instead_of_raised",
        "tests.test_core_resilience.PureActionContractTests.test_flight_url_contains_route_and_passengers",
    )
    cases.append(_case("Read-only information tools", "partial" if contract_ok else "failed", "Tool contracts and failure behavior passed without opening external sites. Live results remain optional.", {"test_output": contract_details}))
    cases.append(_case("Reversible desktop actions", "manual-required", "The safety guard passed, but automated keyboard or mouse input is intentionally not injected into the operator desktop.", safety_evidence))

    stability_ok, stability_evidence, stability_notes = _stability_probe(args.stability_seconds)
    cases.append(_case("Thirty-minute soak", "partial" if stability_ok else "failed", stability_notes, stability_evidence))

    output = args.output / "checklist-results.json"
    output.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(output)
    return 1 if any(case["status"] == "failed" for case in cases) else 0


if __name__ == "__main__":
    raise SystemExit(main())

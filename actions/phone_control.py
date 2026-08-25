"""Phone call and texting via screen automation. Works with any phone/dialer/voip app."""

import subprocess
import os
import time


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _make_call(params: dict) -> str:
    """Initiate a phone call using screen automation."""
    number = str(params.get("number", "") or "").strip()
    contact = str(params.get("contact", "") or "").strip()
    method = str(params.get("method", "auto") or "auto").strip().lower()

    if not number and not contact:
        return "ERROR: Provide a phone number or contact name."

    target = number or contact

    try:
        import pygetwindow as gw
        phone_apps = ["phone", "dialer", "skype", "whatsapp", "discord", "telegram", "teams"]
        open_phones = []
        for w in gw.getAllWindows():
            if w.title and any(app in w.title.lower() for app in phone_apps):
                open_phones.append(w)
    except ImportError:
        open_phones = []

    if method == "auto":
        if open_phones:
            method = "use_open_app"
        else:
            method = "skype"

    if method == "use_open_app" and open_phones:
        w = open_phones[0]
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.5)
        except Exception:
            pass

        try:
            from actions.screen_automation import _click, _type_text, _press_enter, _hotkey
            _hotkey("ctrl+f")
            time.sleep(0.3)
            _type_text(target)
            time.sleep(0.5)
            _press_enter()
            time.sleep(1)
            return f"CALL_INITIATED|Searching for '{target}' in {w.title}. Press call button to connect."
        except Exception as e:
            return f"CALL_FAILED|Could not interact with {w.title}: {e}"

    elif method == "skype":
        try:
            subprocess.Popen(["explorer.exe", "skype:call?phone=" + target],
                           shell=False)
            return f"CALL_INITIATED|Opening Skype to call {target}"
        except Exception:
            pass

    elif method == "tel":
        try:
            os.startfile(f"tel:{target}")
            return f"CALL_INITIATED|Opening default dialer for {target}"
        except Exception:
            pass

    try:
        from actions.screen_automation import _type_text, _press_enter, _hotkey
        _hotkey("win", "s")
        time.sleep(0.5)
        _type_text("phone")
        time.sleep(1)
        _press_enter()
        time.sleep(2)
        _hotkey("ctrl", "f")
        time.sleep(0.3)
        _type_text(target)
        time.sleep(0.5)
        _press_enter()
        time.sleep(1)
        return f"CALL_INITIATED|Opened phone app and searching for {target}. Click call to connect."
    except Exception as e:
        return f"CALL_FAILED|Could not open phone app: {e}"


def _send_text(params: dict) -> str:
    """Send a text message via screen automation."""
    number = str(params.get("number", "") or "").strip()
    contact = str(params.get("contact", "") or "").strip()
    message = str(params.get("message", "") or "").strip()

    if not message:
        return "ERROR: Provide a message to send."
    if not number and not contact:
        return "ERROR: Provide a phone number or contact name."

    target = number or contact

    try:
        import pygetwindow as gw
        msg_apps = ["whatsapp", "messages", "telegram", "discord", "signal", "sms"]
        open_msg = []
        for w in gw.getAllWindows():
            if w.title and any(app in w.title.lower() for app in msg_apps):
                open_msg.append(w)
    except ImportError:
        open_msg = []

    if open_msg:
        w = open_msg[0]
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.5)
        except Exception:
            pass

        try:
            from actions.screen_automation import _click, _type_text, _press_enter, _hotkey
            _hotkey("ctrl+f")
            time.sleep(0.3)
            _type_text(target)
            time.sleep(0.8)
            _press_enter()
            time.sleep(1)
            _type_text(message)
            time.sleep(0.3)
            _press_enter()
            return f"TEXT_SENT|Message sent to {target} via {w.title}: {message[:50]}"
        except Exception as e:
            return f"TEXT_FAILED|Could not send via {w.title}: {e}"

    try:
        from actions.screen_automation import _type_text, _press_enter, _hotkey
        _hotkey("win", "s")
        time.sleep(0.5)
        _type_text("whatsapp")
        time.sleep(1)
        _press_enter()
        time.sleep(2)
        _hotkey("ctrl", "f")
        time.sleep(0.3)
        _type_text(target)
        time.sleep(0.8)
        _press_enter()
        time.sleep(1)
        _type_text(message)
        time.sleep(0.3)
        _press_enter()
        return f"TEXT_SENT|Opened WhatsApp and sent to {target}: {message[:50]}"
    except Exception as e:
        return f"TEXT_FAILED|Could not open messaging app: {e}"


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "call") or "call").lower()
    if action == "call":
        return _make_call(params)
    elif action == "text":
        return _send_text(params)
    return f"Unknown action: {action}. Valid: call, text"

"""Screen automation: click, type, scroll, extract text, find elements on screen.
Uses pyautogui for physical control and OCR/vision for screen reading."""

import subprocess
import os
import time
import json
import re
import ctypes
from pathlib import Path


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1


def _safe_import():
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.3
        return pyautogui
    except ImportError:
        return None


def handle(parameters=None):
    params = parameters or {}
    action = params.get("action", "help")
    target = params.get("target", "")
    value = params.get("value", "")

    handlers = {
        "click": lambda: _click(int(params.get("x", 0)), int(params.get("y", 0))),
        "double_click": lambda: _double_click(int(params.get("x", 0)), int(params.get("y", 0))),
        "right_click": lambda: _right_click(int(params.get("x", 0)), int(params.get("y", 0))),
        "type_text": lambda: _type_text(target),
        "hotkey": lambda: _hotkey(target),
        "scroll": lambda: _scroll(int(target) if target else 3),
        "scroll_down": lambda: _scroll(-int(target) if target else -3),
        "drag": lambda: _drag(int(params.get("x1", 0)), int(params.get("y1", 0)),
                              int(params.get("x2", 0)), int(params.get("y2", 0))),
        "move_mouse": lambda: _move_mouse(int(params.get("x", 0)), int(params.get("y", 0))),
        "screenshot": lambda: _take_screenshot(target),
        "get_screen_size": _get_screen_size,
        "get_mouse_pos": _get_mouse_pos,
        "find_on_screen": lambda: _find_on_screen(target),
        "extract_text": lambda: _extract_text(target),
        "read_screen": _read_screen,
        "list_windows": _list_windows,
        "focus_window": lambda: _focus_window(target),
        "maximize_window": lambda: _maximize_window(target),
        "minimize_window": lambda: _minimize_window(target),
        "close_window": lambda: _close_window(target),
        "resize_window": lambda: _resize_window(target, int(params.get("x", 800)), int(params.get("y", 600))),
        "move_window": lambda: _move_window(target, int(params.get("x", 0)), int(params.get("y", 0))),
        "wait_and_click": lambda: _wait_and_click(target, int(params.get("x", 0)), int(params.get("y", 0))),
        "paste_text": lambda: _paste_text(target),
        "press_enter": _press_enter,
        "press_escape": _press_escape,
        "press_tab": _press_tab,
        "press_backspace": _press_backspace,
        "select_all": _select_all,
        "copy_selection": _copy_selection,
        "undo": _undo,
        "verify_action": lambda: _verify_action(target),
        "help": _help,
    }

    handler = handlers.get(action)
    if handler:
        result = handler()
        return result if isinstance(result, str) else str(result)
    return f"Unknown action: {action}. Available: {', '.join(sorted(handlers.keys()))}"


def _help():
    return """SCREEN AUTOMATION TOOLS:
  click             - Click at x,y coordinates
  double_click      - Double-click at x,y
  right_click       - Right-click at x,y
  type_text         - Type text (target=text to type)
  hotkey            - Press hotkey combo (target=ctrl+c, alt+tab, etc.)
  scroll            - Scroll up (target=amount, default 3)
  scroll_down       - Scroll down
  drag              - Drag from x1,y1 to x2,y2
  move_mouse        - Move mouse to x,y
  screenshot        - Take screenshot (target=filename)
  get_screen_size   - Get screen resolution
  get_mouse_pos     - Get current mouse position
  find_on_screen    - Find element on screen (target=description)
  extract_text      - Extract text from screen area (target=region or empty for full)
  read_screen       - Read what's currently on screen
  list_windows      - List all open windows
  focus_window      - Focus a window (target=window title)
  maximize_window   - Maximize a window
  minimize_window   - Minimize a window
  close_window      - Close a window
  resize_window     - Resize window (target=title, x=width, y=height)
  move_window       - Move window (target=title, x=left, y=top)
  wait_and_click    - Wait for element then click (target=description, x,y)
  paste_text        - Paste text from clipboard (target=text to put in clipboard first)
  press_enter       - Press Enter key
  press_escape      - Press Escape
  press_tab         - Press Tab
  press_backspace   - Press Backspace
  select_all        - Ctrl+A
  copy_selection    - Ctrl+C
  undo              - Ctrl+Z"""


def _click(x, y):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    try:
        pag.click(x, y)
    except Exception as e:
        return f"Click failed: {e}"
    return f"Clicked at ({x}, {y})"


def _double_click(x, y):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    try:
        pag.doubleClick(x, y)
    except Exception as e:
        return f"Double-click failed: {e}"
    return f"Double-clicked at ({x}, {y})"


def _right_click(x, y):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    try:
        pag.rightClick(x, y)
    except Exception as e:
        return f"Right-click failed: {e}"
    return f"Right-clicked at ({x}, {y})"


def _type_text(text):
    if not text:
        return "No text provided"
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.typewrite(text, interval=0.02) if text.isascii() else _paste_and_type(text)
    return f"Typed: {text[:50]}"


def _paste_and_type(text):
    import subprocess
    try:
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, timeout=5,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        pag = _safe_import()
        if pag:
            pag.hotkey("ctrl", "v")
    except Exception:
        pag = _safe_import()
        if pag:
            pag.write(text)


def _paste_text(text):
    if text:
        import subprocess
        try:
            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except Exception:
            pass
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.hotkey("ctrl", "v")
    return f"Pasted text"


def _hotkey(combo):
    if not combo:
        return "Provide hotkey combo (e.g. ctrl+c, alt+tab)"
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    keys = [k.strip() for k in combo.split("+")]
    pag.hotkey(*keys)
    return f"Pressed: {combo}"


def _scroll(amount):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.scroll(amount)
    return f"Scrolled {'up' if amount > 0 else 'down'} {abs(amount)} units"


def _drag(x1, y1, x2, y2):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.moveTo(x1, y1)
    pag.drag(x2 - x1, y2 - y1, duration=0.5)
    return f"Dragged from ({x1},{y1}) to ({x2},{y2})"


def _move_mouse(x, y):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.moveTo(x, y)
    return f"Mouse moved to ({x}, {y})"


def _take_screenshot(filename=""):
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    path = filename or str(Path.home() / "Pictures" / f"screenshot_{int(time.time())}.png")
    img = pag.screenshot()
    img.save(path)
    return f"Screenshot saved: {path}"


def _get_screen_size():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    w, h = pag.size()
    return f"Screen: {w}x{h}"


def _get_mouse_pos():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    x, y = pag.position()
    return f"Mouse at ({x}, {y})"


def _find_on_screen(description):
    if not description:
        return "Provide description of what to find"
    try:
        from actions.computer_control import screen_find
        result = screen_find({"target": description})
        return result
    except Exception as e:
        return f"Find failed: {e}"


def _extract_text(region=""):
    try:
        import pytesseract
        from PIL import ImageGrab
        if region:
            parts = [int(x.strip()) for x in region.split(",")]
            img = ImageGrab.grab(bbox=tuple(parts))
        else:
            img = ImageGrab.grab()
        text = pytesseract.image_to_string(img)
        return f"EXTRACTED TEXT:\n{text[:3000]}" if text.strip() else "No text found"
    except ImportError:
        return "pytesseract not installed. pip install pytesseract"
    except Exception as e:
        return f"OCR failed: {e}"


def _read_screen():
    try:
        from actions.screen_processor import screen_process
        return screen_process({"angle": "screen", "text": "Read everything on screen. List all text, buttons, menus, and UI elements you can see."})
    except Exception as e:
        return f"Screen read failed: {e}"


def _verify_action(expected=""):
    """Capture screen after an action and report what actually happened."""
    import io
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        img_bytes = buf.getvalue()
        mime = "image/jpeg"
    except Exception as e:
        return f"VERIFY_FAILED|Could not capture screen: {e}"

    try:
        from actions.screen_processor import _direct_vision_answer
        if expected:
            prompt = (
                f"The user just attempted: {expected}\n"
                "Look at this screenshot. Did the action succeed? "
                "Report EXACTLY what you see — any error messages, confirmation dialogs, "
                "or the current state. Be specific and concise."
            )
        else:
            prompt = (
                "Describe the current screen state in detail. "
                "List all visible text, buttons, dialogs, error messages, and UI elements."
            )
        result = _direct_vision_answer(img_bytes, mime, prompt)
        return f"VERIFY_OK|{result}"
    except Exception as e:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img)
            if expected:
                return f"VERIFY_OK|After '{expected}': {text[:2000]}"
            return f"VERIFY_OK|Screen text: {text[:2000]}"
        except Exception:
            return f"VERIFY_OK|Screenshot captured but could not analyze. Check manually."


def _list_windows():
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        visible = [w for w in windows if w.title.strip()]
        lines = []
        for i, w in enumerate(visible[:30]):
            lines.append(f"  {i+1}. {w.title[:60]} {'[MINIMIZED]' if w.isMinimized else ''}")
        return f"OPEN WINDOWS ({len(visible)}):\n" + "\n".join(lines)
    except Exception:
        out, _ = _run(["powershell", "-Command",
                       "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Id,ProcessName,MainWindowTitle | Format-Table -AutoSize"], timeout=8)
        return f"OPEN WINDOWS:\n{out}" if out else "Could not list windows"


def _focus_window(title):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            return f"Focused: {w.title}"
    except Exception:
        pass
    try:
        ps = f"(Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}}).MainWindowHandle | ForEach-Object {{ Add-Type -Name Win -Namespace Native -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);' ; [Native.Win]::SetForegroundWindow($_) }}"
        _run(["powershell", "-Command", ps], timeout=5)
        return f"Focused via PowerShell: {title}"
    except Exception:
        pass
    return f"Could not focus: {title}"


def _maximize_window(title):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            w.maximize()
            return f"Maximized: {w.title}"
    except Exception:
        pass
    return f"Could not maximize: {title}"


def _minimize_window(title):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            w.minimize()
            return f"Minimized: {w.title}"
    except Exception:
        pass
    return f"Could not minimize: {title}"


def _close_window(title):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            w.close()
            return f"Closed: {w.title}"
    except Exception:
        pass
    return f"Could not close: {title}"


def _resize_window(title, width, height):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            w.resizeTo(width, height)
            return f"Resized {w.title} to {width}x{height}"
    except Exception:
        pass
    return f"Could not resize: {title}"


def _move_window(title, x, y):
    if not title:
        return "Provide window title"
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            windows = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if windows:
            w = windows[0]
            w.moveTo(x, y)
            return f"Moved {w.title} to ({x}, {y})"
    except Exception:
        pass
    return f"Could not move: {title}"


def _wait_and_click(description, x, y):
    import pyautogui
    pyautogui.FAILSAFE = False
    time.sleep(2)
    if x and y:
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.3)
        pyautogui.click(x, y)
        time.sleep(0.5)
        try:
            from actions.computer_control import _screen_find
            verify = _screen_find(description)
            if verify and (abs(verify[0] - x) > 50 or abs(verify[1] - y) > 50):
                pyautogui.click(verify[0], verify[1])
                return f"Clicked {description} at ({x},{y}), verified at ({verify[0]},{verify[1]}), re-clicked"
        except Exception:
            pass
        return f"Clicked {description} at ({x}, {y})"
    if description:
        try:
            from actions.computer_control import _screen_find
            for attempt in range(3):
                pos = _screen_find(description)
                if pos:
                    pyautogui.moveTo(pos[0], pos[1], duration=0.3)
                    time.sleep(0.3)
                    pyautogui.click(pos[0], pos[1])
                    time.sleep(1)
                    verify = _screen_find(description)
                    if not verify or (abs(verify[0] - pos[0]) < 30 and abs(verify[1] - pos[1]) < 30):
                        return f"Clicked {description} at ({pos[0]}, {pos[1]}) (attempt {attempt+1})"
                    continue
                time.sleep(1)
            return f"Could not find {description} after 3 attempts"
        except Exception as e:
            return f"Click failed: {e}"
    return "Waited 2s but no coordinates or description provided"


def _press_enter():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.press("enter")
    return "Pressed Enter"


def _press_escape():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.press("escape")
    return "Pressed Escape"


def _press_tab():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.press("tab")
    return "Pressed Tab"


def _press_backspace():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.press("backspace")
    return "Pressed Backspace"


def _select_all():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.hotkey("ctrl", "a")
    return "Selected all"


def _copy_selection():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.hotkey("ctrl", "c")
    return "Copied selection"


def _undo():
    pag = _safe_import()
    if not pag:
        return "pyautogui not installed"
    pag.hotkey("ctrl", "z")
    return "Undo"

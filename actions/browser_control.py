"""Browser Automation - pyautogui + playwright browser control.
Handles Freelancer automation, general web browsing, screenshots, form filling.
"""
import time
import json
import subprocess
import ctypes
import logging
import urllib.parse
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

try:
    import pyautogui
    import pyperclip
    import pygetwindow as gw
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    pyautogui.TIMEOUT = 5.0
    _HAS_GUI_DEPS = True
except ImportError:
    _HAS_GUI_DEPS = False

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)


def _safe_clipboard_copy(text: str) -> bool:
    import time
    for attempt in range(3):
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            log.warning("pyperclip.copy failed (attempt %d): %s", attempt + 1, e)
            time.sleep(0.1)
    return False


def _safe_clipboard_paste() -> str:
    try:
        return pyperclip.paste()
    except Exception as e:
        log.warning("pyperclip.paste failed: %s", e)
        return ""


def _normalize_url(url):
    if not url:
        return url
    url = url.strip()
    if not url.startswith(("http://", "https://", "ftp://")):
        url = "https://" + url
    return url


def browser_control(parameters=None, player=None):
    params = parameters or {}
    action = params.get("action", "go_to").lower()
    url = params.get("url", "")
    query = params.get("query", "")
    text = params.get("text", "")
    key = params.get("key", "")
    direction = params.get("direction", "down")
    amount = params.get("amount", 500)
    path_param = params.get("path", "")
    browser_name = params.get("browser", "")

    try:
        from playwright.sync_api import sync_playwright
        _HAS_PLAYWRIGHT = True
    except ImportError:
        _HAS_PLAYWRIGHT = False

    if action == "go_to" and url:
        url = _normalize_url(url)
        if _HAS_PLAYWRIGHT:
            try:
                with sync_playwright() as p:
                    br = p.chromium.launch(headless=False)
                    page = br.new_page()
                    page.goto(url)
                    time.sleep(1)
                    title = page.title()
                    br.close()
                    return f"Opened: {url}\nTitle: {title}"
            except Exception:
                pass
        if _HAS_GUI_DEPS:
            _open_url_pyautogui(url)
            return f"Opened: {url}"
        import webbrowser
        webbrowser.open(url)
        return f"Opened: {url}"

    elif action == "search" and query:
        engine = params.get("engine", "google")
        engines = {
            "google": "https://www.google.com/search?q=",
            "bing": "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
            "yandex": "https://yandex.com/search/?text=",
        }
        search_url = engines.get(engine, engines["google"]) + urllib.parse.quote_plus(query)
        return browser_control({"action": "go_to", "url": search_url}, player)

    elif action == "new_tab" and url:
        url = _normalize_url(url)
        if _HAS_GUI_DEPS:
            _open_url_pyautogui(url)
            return f"Opened in new tab: {url}"
        import webbrowser
        webbrowser.open_new_tab(url)
        return f"Opened in new tab: {url}"

    elif action == "screenshot":
        if _HAS_GUI_DEPS:
            path_out = path_param or str(_DATA_DIR / "screenshots" / f"screen_{int(time.time())}.png")
            Path(path_out).parent.mkdir(parents=True, exist_ok=True)
            img = pyautogui.screenshot()
            img.save(path_out)
            return f"Screenshot saved: {path_out}"
        return "Screenshot requires pyautogui"

    elif action == "get_text":
        if _HAS_GUI_DEPS:
            _focus_active()
            _safe_clipboard_copy("")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            return _safe_clipboard_paste()
        return "get_text requires pyautogui"

    elif action == "get_url":
        if _HAS_GUI_DEPS:
            _focus_active()
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            _safe_clipboard_copy("")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            url_result = _safe_clipboard_paste().strip()
            pyautogui.press("escape")
            time.sleep(0.1)
            return url_result
        return "get_url requires pyautogui"

    elif action == "click":
        if _HAS_GUI_DEPS and text:
            try:
                loc = pyautogui.locateOnScreen(text, confidence=0.7, grayscale=True)
                if loc:
                    center = pyautogui.center(loc)
                    pyautogui.click(center)
                    return f"Clicked: {text}"
            except pyautogui.ImageNotFoundException:
                log.debug("locateOnScreen image not found: %s", text)
            except Exception as e:
                log.debug("locateOnScreen failed: %s", e)
            if text.isdigit():
                pyautogui.click(int(text), int(text))
                return f"Clicked at: {text}"
        return "Could not click element"

    elif action == "type":
        if _HAS_GUI_DEPS and text:
            if _safe_clipboard_copy(text):
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(text, interval=0.02)
            return f"Typed: {text[:50]}..."
        return "Type requires text and pyautogui"

    elif action == "fill_form":
        if _HAS_GUI_DEPS and text:
            if _safe_clipboard_copy(text):
                pyautogui.hotkey("ctrl", "a")
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(text, interval=0.02)
            return f"Filled form with: {text[:50]}..."
        return "Fill form requires text"

    elif action == "press":
        if key:
            if _HAS_GUI_DEPS:
                pyautogui.press(key)
                return f"Pressed: {key}"
        return "Press requires key"

    elif action == "scroll":
        if _HAS_GUI_DEPS:
            clicks = amount // 100
            if direction == "up":
                pyautogui.scroll(clicks)
            else:
                pyautogui.scroll(-clicks)
            return f"Scrolled {direction} {amount}px"
        return "Scroll requires pyautogui"

    elif action == "wait":
        secs = float(text or "2")
        time.sleep(min(secs, 10))
        return f"Waited {secs}s"

    elif action == "select_all_and_copy":
        if _HAS_GUI_DEPS:
            _safe_clipboard_copy("")
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            return _safe_clipboard_paste()
        return "select_all_and_copy requires pyautogui"

    elif action == "smart_click":
        if _HAS_GUI_DEPS and text:
            try:
                loc = pyautogui.locateOnScreen(text, confidence=0.7, grayscale=True)
                if loc:
                    pyautogui.click(pyautogui.center(loc))
                    return f"Smart clicked: {text}"
            except Exception:
                pass
        return "Could not smart click"

    elif action == "smart_type":
        if _HAS_GUI_DEPS and text:
            if _safe_clipboard_copy(text):
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.typewrite(text, interval=0.02)
            return f"Smart typed: {text[:50]}..."
        return "Smart type requires text"

    elif action in ("back", "forward", "reload"):
        if _HAS_GUI_DEPS:
            key_map = {"back": "alt+left", "forward": "alt+right", "reload": "f5"}
            combo = key_map.get(action, "f5")
            pyautogui.hotkey(*combo.split("+"))
            return f"Action: {action}"
        return f"Action {action} requires pyautogui"

    elif action in ("close_tab", "close_all", "close"):
        if _HAS_GUI_DEPS:
            if action == "close_all":
                pyautogui.hotkey("ctrl", "shift", "w")
            else:
                pyautogui.hotkey("ctrl", "w")
            return f"Action: {action}"
        return f"Action {action} requires pyautogui"

    elif action == "list_browsers":
        if _HAS_GUI_DEPS:
            titles = gw.getAllTitles()
            browsers = [t for t in titles if any(b in t.lower() for b in ["chrome", "edge", "firefox", "brave", "opera"])]
            return f"Open browsers: {browsers}" if browsers else "No browser windows found"
        return "list_browsers requires pyautogui"

    elif action == "switch":
        if _HAS_GUI_DEPS and browser_name:
            for title in gw.getAllTitles():
                if browser_name.lower() in title.lower():
                    win = gw.getWindowsWithTitle(title)[0]
                    win.activate()
                    return f"Switched to: {title}"
        return f"Could not find browser: {browser_name}"

    elif action in ("search_jobs", "submit_proposal", "open_dashboard", "open_messages", "open_job", "automation_log"):
        fa = FreelancerAutomation()
        if action == "search_jobs":
            return fa.search_jobs(query or "python")
        elif action == "submit_proposal":
            return fa.submit_proposal(url, text, params.get("budget"))
        elif action == "open_dashboard":
            return fa.open_dashboard()
        elif action == "open_messages":
            return fa.open_messages()
        elif action == "open_job":
            return fa.open_job_page(url)
        elif action == "automation_log":
            return fa.get_log(int(url) if url else 10)

    return f"Unknown browser action: {action}. Available: go_to, search, click, type, scroll, screenshot, get_text, get_url, press, new_tab, close_tab, back, forward, reload, search_jobs, submit_proposal, open_dashboard, open_messages, open_job, automation_log"


def _open_url_pyautogui(url):
    if not _HAS_GUI_DEPS:
        return
    try:
        wins = gw.getAllTitles()
        browser_win = None
        for title in wins:
            if any(b in title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera"]):
                browser_win = gw.getWindowsWithTitle(title)[0]
                break
        if browser_win:
            if browser_win.isMinimized:
                browser_win.restore()
            browser_win.activate()
            time.sleep(0.3)
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.15)
        if _safe_clipboard_copy(url):
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.typewrite(url, interval=0.01)
        time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(1.5)
    except Exception as e:
        log.warning("pyautogui nav failed: %s", e)
        import webbrowser
        webbrowser.open(url)


def _focus_active():
    if _HAS_GUI_DEPS:
        try:
            pyautogui.hotkey("alt")
        except Exception:
            pass


def _check_deps():
    if not _HAS_GUI_DEPS:
        raise RuntimeError("pyautogui, pyperclip, pygetwindow required. pip install pyautogui pyperclip pygetwindow")


def find_browser_window(title_contains=""):
    _check_deps()
    for title in gw.getAllTitles():
        if title_contains.lower() in title.lower():
            wins = gw.getWindowsWithTitle(title)
            if wins:
                return wins[0]
    return None


def focus_browser(title_contains="Freelancer"):
    win = find_browser_window(title_contains)
    if not win:
        return False
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.3)
        return True
    except Exception as e:
        log.warning("Could not focus window: %s", e)
        return False


def navigate_to(url):
    _check_deps()
    if not focus_browser():
        return "No browser window found"
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.15)
    if _safe_clipboard_copy(url):
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.typewrite(url, interval=0.01)
    time.sleep(0.1)
    pyautogui.press("enter")
    time.sleep(2)
    return f"Navigated to: {url}"


def type_text(text, use_clipboard=True):
    _check_deps()
    if use_clipboard:
        if _safe_clipboard_copy(text):
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.typewrite(text, interval=0.02)
    else:
        pyautogui.typewrite(text, interval=0.02)
    time.sleep(0.1)


def press_key(key):
    _check_deps()
    pyautogui.press(key)
    time.sleep(0.1)


def hotkey(*keys):
    _check_deps()
    pyautogui.hotkey(*keys)
    time.sleep(0.1)


def click_at(x, y):
    _check_deps()
    pyautogui.click(x, y)
    time.sleep(0.2)


def screenshot_and_save(path=None):
    _check_deps()
    if path is None:
        path = str(_DATA_DIR / "screenshots" / f"screen_{int(time.time())}.png")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot()
    img.save(path)
    return path


def scroll_down(clicks=3):
    _check_deps()
    pyautogui.scroll(-clicks)
    time.sleep(0.2)


def scroll_up(clicks=3):
    _check_deps()
    pyautogui.scroll(clicks)
    time.sleep(0.2)


def find_and_click_text_on_screen(text):
    _check_deps()
    try:
        location = pyautogui.locateOnScreen(text, confidence=0.8, grayscale=True)
        if location:
            center = pyautogui.center(location)
            pyautogui.click(center)
            return True
    except pyautogui.ImageNotFoundException:
        log.debug("find_and_click_text_on_screen: image not found: %s", text)
    except Exception as e:
        log.debug("find_and_click_text_on_screen failed: %s", e)
    return False


class FreelancerAutomation:
    BASE = "https://www.freelancer.com"

    def __init__(self):
        self._log_file = _DATA_DIR / "automation_log.json"
        self._log_entries = self._load_log()

    def _load_log(self):
        if self._log_file.exists():
            try:
                return json.loads(self._log_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _log_action(self, action, detail, success=True):
        entry = {
            "time": datetime.now().isoformat(),
            "action": action,
            "detail": detail[:200],
            "success": success,
        }
        self._log_entries.append(entry)
        if len(self._log_entries) > 200:
            self._log_entries = self._log_entries[-200:]
        self._log_file.write_text(json.dumps(self._log_entries, indent=2), encoding="utf-8")
        return entry

    def open_job_page(self, job_url):
        if not focus_browser("freelancer"):
            result = navigate_to(job_url)
        else:
            result = navigate_to(job_url)
        self._log_action("open_job", job_url, "Navigated" in str(result))
        return result

    def submit_proposal(self, job_url, proposal_text, budget=None):
        steps = []
        steps.append(f"1. Navigating to {job_url}")
        nav_result = navigate_to(job_url)
        steps.append(f"   {nav_result}")
        time.sleep(2)

        steps.append("2. Looking for 'Place a Bid' button...")
        focus_browser("freelancer")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        type_text("Place a Bid")
        time.sleep(0.5)
        pyautogui.press("escape")
        time.sleep(0.5)
        scroll_down(5)
        time.sleep(0.5)

        steps.append("3. Clicking bid button area...")
        screen_w, screen_h = pyautogui.size()
        click_at(screen_w // 2, int(screen_h * 0.6))
        time.sleep(1)

        steps.append("4. Entering proposal text...")
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        type_text("Description")
        time.sleep(0.5)
        pyautogui.press("escape")
        time.sleep(0.5)
        click_at(screen_w // 2, int(screen_h * 0.5))
        time.sleep(0.3)
        if _safe_clipboard_copy(proposal_text):
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)

        if budget:
            steps.append(f"5. Setting budget to ${budget}...")
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)
            type_text("Bid Amount")
            time.sleep(0.5)
            pyautogui.press("escape")
            time.sleep(0.3)
            click_at(screen_w // 2, int(screen_h * 0.4))
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            if _safe_clipboard_copy(str(budget)):
                pyautogui.hotkey("ctrl", "v")
            time.sleep(0.3)

        steps.append("6. PAUSED - Review and submit manually.")
        steps.append("   Proposal text has been pasted. Click Submit to finish.")
        self._log_action("submit_proposal", f"{job_url} - {proposal_text[:80]}...", True)
        return "\n".join(steps)

    def search_jobs(self, query="python", page=1):
        url = f"{self.BASE}/jobs/?keyword={query.replace(' ', '+')}&page={page}"
        result = navigate_to(url)
        time.sleep(2)
        focus_browser("freelancer")
        time.sleep(1)
        self._log_action("search_jobs", f"query={query} page={page}", True)
        return f"Opened Freelancer search: {query} (page {page})\n{result}"

    def open_dashboard(self):
        result = navigate_to(f"{self.BASE}/users/settings/earnings/")
        self._log_action("open_dashboard", "earnings page", True)
        return result

    def open_messages(self):
        result = navigate_to(f"{self.BASE}/messages/")
        self._log_action("open_messages", "inbox", True)
        return result

    def take_screenshot(self):
        path = screenshot_and_save()
        self._log_action("screenshot", path, True)
        return f"Screenshot saved: {path}"

    def get_log(self, count=10):
        entries = self._log_entries[-count:]
        lines = [f"[{e['time']}] {e['action']}: {e['detail'][:80]} ({'OK' if e['success'] else 'FAIL'})"
                 for e in entries]
        return "\n".join(lines) if lines else "No automation log entries"


def handle(params=None):
    params = params or {}
    action = params.get("action", "status")
    target = params.get("target", "")
    value = params.get("value", "")

    fa = FreelancerAutomation()
    actions = {
        "open": lambda: fa.open_job_page(target),
        "search": lambda: fa.search_jobs(target or "python"),
        "bid": lambda: fa.submit_proposal(target, value),
        "dashboard": lambda: fa.open_dashboard(),
        "messages": lambda: fa.open_messages(),
        "screenshot": lambda: fa.take_screenshot(),
        "log": lambda: fa.get_log(int(target) if target else 10),
        "focus": lambda: "Focused" if focus_browser(target or "freelancer") else "Not found",
        "nav": lambda: navigate_to(target),
        "type": lambda: (type_text(target), "Typed")[1] if target else "Provide text",
        "click": lambda: (click_at(*[int(x) for x in target.split(",")]) if "," in target else "Provide x,y"),
        "scroll": lambda: scroll_down(int(target) if target else 3),
        "screenshot_path": lambda: screenshot_and_save(target),
    }

    fn = actions.get(action)
    if fn:
        result = fn()
        return str(result)
    return f"Unknown: {action}. Available: {', '.join(sorted(actions.keys()))}"

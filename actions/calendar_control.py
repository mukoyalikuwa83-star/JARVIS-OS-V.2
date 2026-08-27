"""Calendar control: create, list, update, delete events via Google Calendar browser automation."""

import json
import time
from datetime import datetime, timedelta


def _open_google_calendar(browser="chrome"):
    try:
        from actions.browser_control import _BrowserSession
        ctrl = _BrowserSession()
        return ctrl, ctrl.go_to(parameters={"url": "https://calendar.google.com", "browser": browser})
    except Exception:
        import webbrowser
        webbrowser.open("https://calendar.google.com")
        time.sleep(3)
        return None, "Opened Google Calendar in browser"


def _parse_relative_date(text):
    now = datetime.now()
    text = text.lower().strip()
    if "today" in text:
        return now
    if "tomorrow" in text:
        return now + timedelta(days=1)
    if "next week" in text:
        return now + timedelta(weeks=1)
    if "next monday" in text:
        days_ahead = 0 - now.weekday() + 7
        if days_ahead <= 0:
            days_ahead += 7
        return now + timedelta(days=days_ahead)
    if "next tuesday" in text:
        days_ahead = 1 - now.weekday() + 7
        if days_ahead <= 0:
            days_ahead += 7
        return now + timedelta(days=days_ahead)
    if "next wednesday" in text:
        days_ahead = 2 - now.weekday() + 7
        if days_ahead <= 0:
            days_ahead += 7
        return now + timedelta(days=days_ahead)
    if "next thursday" in text:
        days_ahead = 3 - now.weekday() + 7
        if days_ahead <= 0:
            days_ahead += 7
        return now + timedelta(days=days_ahead)
    if "next friday" in text:
        days_ahead = 4 - now.weekday() + 7
        if days_ahead <= 0:
            days_ahead += 7
        return now + timedelta(days=days_ahead)
    for i, day_name in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        if day_name in text:
            days_ahead = i - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return now + timedelta(days=days_ahead)
    return now


def create_event(params=None):
    title = (params or {}).get("title", "Untitled Event")
    date_str = (params or {}).get("date", "today")
    time_str = (params or {}).get("time", "")
    duration_min = int((params or {}).get("duration", 60))
    description = (params or {}).get("description", "")
    location = (params or {}).get("location", "")
    browser = (params or {}).get("browser", "chrome")

    event_date = _parse_relative_date(date_str)
    date_formatted = event_date.strftime("%Y-%m-%d")

    ctrl, _ = _open_google_calendar(browser)
    if ctrl is None:
        return json.dumps({"result": f"Google Calendar opened — please create '{title}' on {date_formatted} manually",
                           "title": title, "date": date_formatted, "time": time_str})
    time.sleep(3)

    try:
        create_btn = ctrl.page.get_by_role("button", name="Create").first
        create_btn.click(timeout=5000)
        time.sleep(1)

        event_btn = ctrl.page.get_by_role("menuitem", name="Event").first
        event_btn.click(timeout=3000)
        time.sleep(1)

        title_input = ctrl.page.get_by_placeholder("Add title")
        title_input.click(timeout=3000)
        title_input.fill(title)
        time.sleep(0.5)

        if time_str:
            time_parts = time_str.replace(".", ":").split(":")
            hour = time_parts[0].strip()
            minute = time_parts[1].strip() if len(time_parts) > 1 else "00"
            hour = hour.zfill(2)
            minute = minute.zfill(2)
            time_value = f"{hour}:{minute}"

            start_inputs = ctrl.page.locator("input[aria-label*='Start time'], input[placeholder*='Start time']")
            if start_inputs.count() > 0:
                start_inputs.first.click()
                start_inputs.first.fill(time_value)
                start_inputs.first.press("Enter")
                time.sleep(0.5)

        if description:
            desc_btn = ctrl.page.get_by_role("button", name="Add description")
            if desc_btn.count() > 0:
                desc_btn.first.click(timeout=2000)
                time.sleep(0.5)
                desc_area = ctrl.page.locator("[contenteditable='true']")
                if desc_area.count() > 0:
                    desc_area.first.fill(description)

        if location:
            loc_input = ctrl.page.get_by_placeholder("Add location")
            if loc_input.count() > 0:
                loc_input.first.click()
                loc_input.first.fill(location)
                time.sleep(1)
                ctrl.page.keyboard.press("Enter")
                time.sleep(0.5)

        save_btn = ctrl.page.get_by_role("button", name="Save")
        save_btn.click(timeout=3000)
        time.sleep(2)

        return json.dumps({"result": f"Event '{title}' created on {date_formatted}" + (f" at {time_str}" if time_str else ""),
                           "title": title, "date": date_formatted, "time": time_str})
    except Exception as e:
        return json.dumps({"error": f"Failed to create event: {e}", "hint": "Make sure you are signed into Google Calendar"})


def list_events(params=None):
    browser = (params or {}).get("browser", "chrome")
    date_str = (params or {}).get("date", "today")
    # headless default ON: never pops a browser during background checks
    headless = (params or {}).get("headless", True)
    event_date = _parse_relative_date(date_str)

    if headless:
        return _list_events_local(event_date)

    ctrl, _ = _open_google_calendar(browser)
    if ctrl is None:
        return json.dumps({"date": event_date.strftime("%Y-%m-%d"), "events": [],
                           "note": "Google Calendar opened in browser — please sign in and check manually"})
    time.sleep(3)

    try:
        day_btn = ctrl.page.get_by_role("button", name="Day")
        if day_btn.count() > 0:
            day_btn.first.click(timeout=3000)
            time.sleep(1)

        events = []
        event_elements = ctrl.page.locator("[data-eventid], [data-eventchip], .fc-event, .calendar-event")
        count = event_elements.count()
        for i in range(min(count, 10)):
            try:
                text = event_elements.nth(i).inner_text(timeout=2000)
                if text.strip():
                    events.append(text.strip())
            except Exception:
                continue

        if not events:
            main_content = ctrl.page.locator("main, [role='main'], .tEhMVd")
            if main_content.count() > 0:
                text = main_content.first.inner_text(timeout=3000)
                lines = [l.strip() for l in text.split("\n") if l.strip() and ":" in l]
                events = lines[:10]

        return json.dumps({"date": event_date.strftime("%Y-%m-%d"), "events": events,
                           "count": len(events)})
    except Exception as e:
        return json.dumps({"error": f"Failed to list events: {e}"})


def _list_events_local(event_date):
    """Headless calendar read from the local reminders/agenda store. Never opens a browser."""
    import datetime
    events = []
    now = datetime.datetime.now()

    def add_from_json(path):
        from pathlib import Path
        try:
            if not Path(path).exists():
                return
            import json as _json
            data = _json.loads(Path(path).read_text(encoding="utf-8"))
            for item in data if isinstance(data, list) else data.get("reminders", []):
                if not isinstance(item, dict):
                    continue
                when = item.get("time") or item.get("when") or item.get("datetime")
                title = item.get("title") or item.get("text") or item.get("message")
                if not when or not title:
                    continue
                try:
                    t = datetime.datetime.fromisoformat(str(when).replace("Z", "+00:00").replace("T", " "))
                    if t.tzinfo:
                        t = t.astimezone().replace(tzinfo=None)
                except Exception:
                    continue
                if event_date.date() == t.date():
                    events.append(f"{t.strftime('%I:%M %p')} - {title}")
        except Exception:
            pass

    for p in (".jarvis/reminders.json", "memory/reminders.json", ".jarvis/agenda.json"):
        add_from_json(p)

    events.sort()
    if not events:
        return json.dumps({"date": event_date.strftime("%Y-%m-%d"), "events": [],
                           "count": 0, "note": "No events found locally"})
    return json.dumps({"date": event_date.strftime("%Y-%m-%d"), "events": events,
                       "count": len(events)})


def delete_event(params=None):
    title = (params or {}).get("title", "")
    browser = (params or {}).get("browser", "chrome")

    if not title:
        return json.dumps({"error": "Provide 'title' of the event to delete."})

    ctrl, _ = _open_google_calendar(browser)
    if ctrl is None:
        return json.dumps({"result": f"Google Calendar opened — please delete '{title}' manually"})
    time.sleep(3)

    try:
        search_btn = ctrl.page.get_by_role("button", name="Search")
        if search_btn.count() > 0:
            search_btn.first.click(timeout=3000)
            time.sleep(1)
            search_input = ctrl.page.get_by_placeholder("Search")
            if search_input.count() > 0:
                search_input.first.fill(title)
                search_input.first.press("Enter")
                time.sleep(2)

        event_link = ctrl.page.get_by_role("link", name=title)
        if event_link.count() > 0:
            event_link.first.click(timeout=5000)
            time.sleep(2)

            more_btn = ctrl.page.get_by_role("button", name="Options")
            if more_btn.count() > 0:
                more_btn.first.click(timeout=3000)
                time.sleep(1)

            delete_btn = ctrl.page.get_by_role("menuitem", name="Delete")
            if delete_btn.count() > 0:
                delete_btn.first.click(timeout=3000)
                time.sleep(1)

                confirm_btn = ctrl.page.get_by_role("button", name="Delete")
                if confirm_btn.count() > 0:
                    confirm_btn.first.click(timeout=3000)
                    time.sleep(1)

                return json.dumps({"result": f"Event '{title}' deleted."})

        return json.dumps({"error": f"Event '{title}' not found.", "hint": "Check the exact title"})
    except Exception as e:
        return json.dumps({"error": f"Failed to delete event: {e}"})


ACTIONS = {
    "create": create_event,
    "list": list_events,
    "delete": delete_event,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "list")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})

"""Daily briefings: morning summary of weather, calendar, news, tasks."""

import json
import os
import ssl
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent


def get_weather_summary(params=None):
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    city = (params or {}).get("city", "")
    if not city:
        try:
            req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            data = json.loads(resp.read())
            city = data.get("city", "Johannesburg")
        except Exception:
            city = "Johannesburg"
    try:
        url = f"https://wttr.in/{city}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.loads(resp.read())
        current = data.get("current_condition", [{}])[0]
        today = data.get("weather", [{}])[0] if data.get("weather") else {}
        return json.dumps({
            "city": city,
            "temp_c": current.get("temp_C", "?"),
            "feels_like_c": current.get("FeelsLikeC", "?"),
            "description": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "humidity": current.get("humidity", "?"),
            "wind_kmph": current.get("windspeedKmph", "?"),
            "high_c": today.get("maxtempC", "?"),
            "low_c": today.get("mintempC", "?"),
            "sunrise": today.get("astronomy", [{}])[0].get("sunrise", "?"),
            "sunset": today.get("astronomy", [{}])[0].get("sunset", "?"),
        })
    except Exception as e:
        return json.dumps({"error": str(e)[:200]})


def get_news_headlines(params=None):
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    count = int((params or {}).get("count", 5))
    try:
        url = "https://newsapi.org/v2/top-headlines?country=us&pageSize=10"
        api_key = os.environ.get("NEWS_API_KEY", "")
        if api_key:
            url += f"&apiKey={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = json.loads(resp.read())
            articles = data.get("articles", [])[:count]
            return json.dumps({
                "headlines": [{"title": a.get("title", ""), "source": a.get("source", {}).get("name", ""),
                               "url": a.get("url", "")} for a in articles],
                "count": len(articles),
            })
    except Exception:
        pass
    try:
        url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        content = resp.read().decode("utf-8", errors="replace")
        titles = []
        for line in content.split("<title>"):
            if "</title>" in line:
                title = line.split("</title>")[0].strip()
                if title and title != "RSS" and len(title) > 10:
                    titles.append(title)
                    if len(titles) >= count:
                        break
        return json.dumps({"headlines": [{"title": t, "source": "Google News"} for t in titles], "count": len(titles)})
    except Exception as e:
        return json.dumps({"error": str(e)[:200]})


def build_morning_briefing(params=None):
    parts = []
    now = datetime.now()
    parts.append(f"Good {'morning' if now.hour < 12 else 'afternoon' if now.hour < 17 else 'evening'}.")
    parts.append(f"Today is {now.strftime('%A, %B %d, %Y')}.")
    try:
        weather = json.loads(get_weather_summary(params))
        if "error" not in weather:
            parts.append(f"Weather in {weather['city']}: {weather['temp_c']}°C, {weather['description']}. "
                        f"High {weather['high_c']}°C, Low {weather['low_c']}°C.")
    except Exception:
        pass
    try:
        news = json.loads(get_news_headlines({"count": 3}))
        if news.get("headlines"):
            parts.append("Top headlines:")
            for h in news["headlines"]:
                parts.append(f"  - {h['title']}")
    except Exception:
        pass
    return json.dumps({"briefing": "\n".join(parts), "timestamp": now.isoformat()})


ACTIONS = {
    "weather": get_weather_summary,
    "news": get_news_headlines,
    "morning_briefing": build_morning_briefing,
}


def handle(parameters=None, **_kwargs):
    action = str((parameters or {}).get("action", "morning_briefing")).lower()
    fn = ACTIONS.get(action)
    if fn:
        return fn(parameters)
    return json.dumps({"error": f"Unknown action: {action}. Valid: {', '.join(ACTIONS)}"})

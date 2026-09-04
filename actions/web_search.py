#web_search.py
import json
import os
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            key = data.get("gemini_api_key") or data.get("GEMINI_API_KEY")
            if key:
                return key
    except Exception:
        pass

    raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or config/api_keys.json['gemini_api_key'].")


def _gemini_search(query: str) -> str:
    from google import genai

    client   = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )

    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    # Try ddgs first (new package name)
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
        if results:
            return results
    except Exception:
        pass

    # Fallback: old duckduckgo_search package
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
        if results:
            return results
    except Exception:
        pass

    # Final fallback: HTTP-based Bing search
    try:
        import requests
        from urllib.parse import quote_plus
        from html.parser import HTMLParser

        url = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            class BingParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in_h2 = False
                    self._title = ""
                    self._results = []
                def handle_starttag(self, tag, attrs):
                    if tag == "h2":
                        self._in_h2 = True
                        self._title = ""
                def handle_data(self, data):
                    if self._in_h2:
                        self._title += data
                def handle_endtag(self, tag):
                    if tag == "h2" and self._in_h2:
                        self._in_h2 = False
                        if self._title.strip():
                            self._results.append({"title": self._title.strip(), "snippet": "", "url": ""})
            parser = BingParser()
            parser.feed(resp.text)
            return parser._results[:max_results]
    except Exception:
        pass

    return []


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _fast_search(query: str, max_results: int = 6) -> list[dict]:
    """Direct HTTP search via DuckDuckGo HTML — no API key, no package needed."""
    try:
        import requests
        from urllib.parse import quote_plus
        from html.parser import HTMLParser

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return []

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self._results = []
                self._in_result = False
                self._in_snippet = False
                self._current = {}
                self._depth = 0
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                cls = attrs_dict.get("class", "")
                if tag == "a" and "result__a" in cls:
                    self._in_result = True
                    self._current = {"title": "", "snippet": "", "url": attrs_dict.get("href", "")}
                elif tag == "a" and "result__snippet" in cls:
                    self._in_snippet = True
            def handle_data(self, data):
                if self._in_result:
                    self._current["title"] += data
                elif self._in_snippet:
                    self._current["snippet"] += data
            def handle_endtag(self, tag):
                if tag == "a" and self._in_result:
                    self._in_result = False
                elif tag == "a" and self._in_snippet:
                    self._in_snippet = False
                    if self._current.get("title"):
                        self._results.append(self._current)
                    self._current = {}

        parser = DDGParser()
        parser.feed(resp.text)
        return parser._results[:max_results]
    except Exception:
        return []


def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {e} — falling back to DDG")

    # DDG fallback: fetch results per item and merge
    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
    return "\n".join(lines)

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query."

    if items and mode != "compare":
        mode = "compare"

    if player:
        player.write_log(f"[Search] {query or ', '.join(items)}")

    print(f"[WebSearch] 🔍 Query: {query!r}  Mode: {mode}")

    try:
        if mode == "compare" and items:
            print(f"[WebSearch] 📊 Comparing: {items}")
            result = _compare(items, aspect)
            print("[WebSearch] ✅ Compare done.")
            return result

        # Try fast direct search first (no API key, ~1-2s)
        print("[WebSearch] ⚡ Trying fast search...")
        results = _fast_search(query)
        if results:
            result = _format_ddg(query, results)
            print(f"[WebSearch] ✅ Fast search: {len(results)} result(s).")
            return result

        # Fallback to Gemini (richer but slower)
        print("[WebSearch] 🌐 Trying Gemini...")
        try:
            result = _gemini_search(query)
            print("[WebSearch] ✅ Gemini OK.")
            return result
        except Exception as e:
            print(f"[WebSearch] ⚠️ Gemini failed ({e}) — trying DDG package...")
            results = _ddg_search(query)
            result  = _format_ddg(query, results)
            print(f"[WebSearch] ✅ DDG: {len(results)} result(s).")
            return result

    except Exception as e:
        print(f"[WebSearch] ❌ All backends failed: {e}")
        return f"Search failed: {e}"

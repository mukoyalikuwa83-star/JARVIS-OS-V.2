"""Sing songs by looking up lyrics and delivering them rhythmically via Gemini Live voice."""

import re
import ssl
import urllib.request
import urllib.parse
import json


_LYRICS_API = "https://api.lyrics.ovh/v1"

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _clean_lyrics(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    return "\n".join(lines)


def lookup_lyrics(artist: str, title: str) -> dict:
    """Fetch lyrics from lyrics.ovh API."""
    artist_enc = urllib.parse.quote(artist.strip())
    title_enc = urllib.parse.quote(title.strip())
    url = f"{_LYRICS_API}/{artist_enc}/{title_enc}"
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-OS/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=5, context=_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("lyrics", "")
            if not raw:
                return {"ok": False, "error": "No lyrics found."}
            return {
                "ok": True,
                "artist": artist,
                "title": title,
                "lyrics": _clean_lyrics(raw),
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ok": False, "error": f"Song not found: {artist} - {title}"}
        return {"ok": False, "error": f"Lyrics API error: {e.code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _format_for_singing(lyrics: str) -> str:
    """Format lyrics with rhythmic markers for voice delivery."""
    lines = lyrics.split("\n")
    formatted = []
    for line in lines:
        line = line.strip()
        if not line:
            formatted.append("... ...")
            continue
        if len(line) > 60:
            mid = len(line) // 2
            space = line.rfind(" ", 0, mid)
            if space > 20:
                formatted.append(line[:space] + " ... " + line[space + 1:])
            else:
                formatted.append(line)
        else:
            formatted.append(line)
    return "\n".join(formatted)


def sing(params: dict) -> str:
    """Main singing entry point."""
    artist = str(params.get("artist", "") or "").strip()
    title = str(params.get("title", "") or params.get("song", "") or "").strip()
    query = str(params.get("query", "") or "").strip()

    if not artist and not title and query:
        parts = query.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts[0].strip(), parts[1].strip()
        else:
            parts = query.split(" by ", 1)
            if len(parts) == 2:
                title, artist = parts[0].strip(), parts[1].strip()
            else:
                title = query

    if not title:
        return "ERROR: Provide a song title. Usage: sing(title='Bohemian Rhapsody', artist='Queen')"

    if not artist:
        artist = "unknown"

    result = lookup_lyrics(artist, title)
    if not result.get("ok"):
        return (
            f"🎤 I want to sing: {artist} - {title}\n\n"
            f"[LYRICS_UNAVAILABLE — You know this song! Sing it from memory using your own knowledge. "
            f"Deliver the lyrics rhythmically with emotion, pausing at natural breaks. "
            f"Start with: 'Let me sing {title} by {artist}...']"
        )

    formatted = _format_for_singing(result["lyrics"])
    lines = formatted.split("\n")

    singing_output = (
        f"🎤 Now singing: {result['artist']} - {result['title']}\n\n"
        f"{formatted}\n\n"
        f"[{len(lines)} lines]"
    )

    return singing_output


def handle(params: dict) -> str:
    """Tool handler compatible with main.py dispatch."""
    return sing(params)

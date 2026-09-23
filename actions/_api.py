"""Shared HTTP helper using curl instead of requests/urllib for reliability."""
import subprocess
import json as _json
import os
import time
from pathlib import Path

CURL = r"C:\Windows\System32\curl.exe"
if not os.path.exists(CURL):
    CURL = "curl"

MAX_RETRIES = 3
RETRY_DELAY = 2


def _load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http_get(url, params=None, headers=None, timeout=20, retries=MAX_RETRIES):
    _load_env()
    import urllib.parse
    if params:
        qs = urllib.parse.urlencode(params)
        url = url + ("&" if "?" in url else "?") + qs
    cmd = [CURL, "-s", "-m", str(timeout), url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    last_err = ""
    for attempt in range(retries):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip(), 0
            last_err = proc.stderr.strip() or f"rc={proc.returncode}"
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return last_err, -1


def http_post(url, data=None, files=None, headers=None, timeout=30, form_type="multipart", retries=MAX_RETRIES, json=None):
    _load_env()
    cmd = [CURL, "-s", "-m", str(timeout), "-X", "POST"]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    if files:
        for field, (fname, filepath, ctype) in files.items():
            cmd.extend(["-F", f"{field}=@{filepath};type={ctype}"])
    if json is not None:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["--data-binary", _json.dumps(json)])
    elif data:
        if form_type == "urlencoded":
            for k, v in data.items():
                cmd.extend(["--data-urlencode", f"{k}={v}"])
        else:
            for k, v in data.items():
                cmd.extend(["-F", f"{k}={v}"])
    cmd.append(url)
    last_err = ""
    for attempt in range(retries):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip(), 0
            last_err = proc.stderr.strip() or f"rc={proc.returncode}"
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return last_err, -1


def http_put(url, data=None, headers=None, timeout=20, retries=MAX_RETRIES, form_type="urlencoded"):
    """HTTP PUT. By default sends form-urlencoded data (Gumroad API uses it for product updates)."""
    _load_env()
    cmd = [CURL, "-s", "-m", str(timeout), "-X", "PUT"]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    if data:
        if form_type == "json":
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["--data-binary", json.dumps(data)])
        else:
            for k, v in data.items():
                cmd.extend(["--data-urlencode", f"{k}={v}"])
    cmd.append(url)
    last_err = ""
    for attempt in range(retries):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip(), 0
            last_err = proc.stderr.strip() or f"rc={proc.returncode}"
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return last_err, -1

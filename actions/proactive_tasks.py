"""Proactive auto-task mode — runs background jobs like content creation, scheduling, side hustles."""

import json
import time
import threading
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent
_JOBS_FILE = _BASE_DIR / ".jarvis" / "auto_jobs.json"


def _load_jobs() -> list[dict]:
    try:
        return json.loads(_JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_jobs(jobs: list[dict]):
    _JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _JOBS_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def add_job(params: dict) -> str:
    """Add a proactive job to the queue."""
    job_type = str(params.get("type", "") or "").strip()
    description = str(params.get("description", "") or "").strip()
    schedule = str(params.get("schedule", "once") or "once").strip()
    params_data = params.get("params", {})

    if not job_type or not description:
        return "ERROR: Provide type and description."

    valid_types = [
        "content_creation", "social_post", "data_entry", "email_draft",
        "file_organize", "report_generate", "reminder", "research",
        "monitor", "custom",
    ]
    if job_type not in valid_types:
        return f"ERROR: Invalid type. Valid: {', '.join(valid_types)}"

    job = {
        "id": f"job_{int(time.time())}",
        "type": job_type,
        "description": description,
        "schedule": schedule,
        "params": params_data,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "last_run": None,
        "run_count": 0,
        "active": True,
    }

    jobs = _load_jobs()
    jobs.append(job)
    _save_jobs(jobs)
    return f"JOB_ADDED|{job['id']}|{job_type}: {description} (schedule: {schedule})"


def list_jobs() -> str:
    """List all proactive jobs."""
    jobs = _load_jobs()
    if not jobs:
        return "No proactive jobs configured."
    lines = []
    for j in jobs:
        status = "ACTIVE" if j.get("active") else "PAUSED"
        runs = j.get("run_count", 0)
        last = j.get("last_run", "never")
        lines.append(f"  [{status}] {j['id']}: {j['type']} — {j['description']} (runs: {runs}, last: {last})")
    return f"PROACTIVE JOBS ({len(jobs)}):\n" + "\n".join(lines)


def pause_job(params: dict) -> str:
    """Pause a proactive job."""
    job_id = str(params.get("job_id", "") or "").strip()
    jobs = _load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["active"] = False
            _save_jobs(jobs)
            return f"PAUSED|{job_id}"
    return f"ERROR: Job {job_id} not found."


def resume_job(params: dict) -> str:
    """Resume a proactive job."""
    job_id = str(params.get("job_id", "") or "").strip()
    jobs = _load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["active"] = True
            _save_jobs(jobs)
            return f"RESUMED|{job_id}"
    return f"ERROR: Job {job_id} not found."


def delete_job(params: dict) -> str:
    """Delete a proactive job."""
    job_id = str(params.get("job_id", "") or "").strip()
    jobs = _load_jobs()
    before = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id]
    if len(jobs) < before:
        _save_jobs(jobs)
        return f"DELETED|{job_id}"
    return f"ERROR: Job {job_id} not found."


def get_pending_jobs() -> list[dict]:
    """Get jobs that are due to run."""
    jobs = _load_jobs()
    pending = []
    now = time.time()
    for j in jobs:
        if not j.get("active"):
            continue
        schedule = j.get("schedule", "once")
        last_run = j.get("last_run")
        if schedule == "once" and not last_run:
            pending.append(j)
        elif schedule == "hourly" and (not last_run or (now - time.mktime(time.strptime(last_run, "%Y-%m-%d %H:%M"))) > 3600):
            pending.append(j)
        elif schedule == "daily" and (not last_run or (now - time.mktime(time.strptime(last_run, "%Y-%m-%d %H:%M"))) > 86400):
            pending.append(j)
    return pending


def mark_job_run(job_id: str):
    """Mark a job as run."""
    jobs = _load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["last_run"] = time.strftime("%Y-%m-%d %H:%M")
            j["run_count"] = j.get("run_count", 0) + 1
            if j.get("schedule") == "once":
                j["active"] = False
            _save_jobs(jobs)
            return


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "list") or "list").lower()
    if action == "add":
        return add_job(params)
    elif action == "list":
        return list_jobs()
    elif action == "pause":
        return pause_job(params)
    elif action == "resume":
        return resume_job(params)
    elif action == "delete":
        return delete_job(params)
    return f"Unknown action: {action}. Valid: add, list, pause, resume, delete"

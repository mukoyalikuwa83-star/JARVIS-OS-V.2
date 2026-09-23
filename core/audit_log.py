"""
Audit Log — Appendix C: Immutable append-only log per Part 4.5.
Every action writes here. Dashboards and voice read ONLY from this.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading

from actions._api import _load_env

_AUDIT_LOG = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
_AUDIT_LOCK = threading.Lock()

_load_env()

def write_audit_entry(
    domain: str,
    action_proposed: str,
    screening_result: str,  # "passed" | "rejected:<reason>"
    gate_result: str,       # "auto_approved:<level>" | "pending_approval" | "approved_by_boss" | "denied"
    execution_result: str,  # "success" | "failed:<reason>"
    real_outcome: Any,
    reasoning_summary: str,
    credential_used: str = "none",  # token name only, never value
    entry_id: Optional[str] = None,
    timestamp_utc: Optional[str] = None
) -> str:
    """
    Write an immutable audit log entry per Appendix C schema.
    Returns the entry_id.
    """
    entry = {
        "entry_id": entry_id or str(uuid.uuid4()),
        "timestamp_utc": timestamp_utc or datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "action_proposed": action_proposed,
        "screening_result": screening_result,
        "gate_result": gate_result,
        "execution_result": execution_result,
        "real_outcome": real_outcome,
        "reasoning_summary": reasoning_summary,
        "credential_used": credential_used
    }
    
    # Validate required fields
    required = ["entry_id", "timestamp_utc", "domain", "action_proposed", 
                "screening_result", "gate_result", "execution_result", 
                "real_outcome", "reasoning_summary", "credential_used"]
    for field in required:
        if field not in entry:
            raise ValueError(f"Missing required field: {field}")
            
    # Atomic write
    line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
    
    with _AUDIT_LOCK:
        log_path = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            
    return entry["entry_id"]

def read_audit_log(
    domain: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 1000
) -> List[Dict]:
    """Read audit log entries, optionally filtered."""
    log_path = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
    if not log_path.exists():
        return []
        
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if domain and entry.get("domain") != domain:
                    continue
                if since and entry.get("timestamp_utc", "") < since:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue
                
    # Sort by timestamp descending
    entries.sort(key=lambda x: x.get("timestamp_utc", ""), reverse=True)
    return entries[:limit]

def get_audit_stats() -> Dict:
    """Get audit log statistics."""
    log_path = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
    if not log_path.exists():
        return {"total_entries": 0, "by_domain": {}, "by_result": {}}
        
    stats = {"total_entries": 0, "by_domain": {}, "by_result": {}}
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                stats["total_entries"] += 1
                domain = entry.get("domain", "unknown")
                stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1
                result = entry.get("execution_result", "unknown")
                stats["by_result"][result] = stats["by_result"].get(result, 0) + 1
            except json.JSONDecodeError:
                continue
    return stats

def verify_log_integrity() -> Dict:
    """Verify audit log integrity — no partial entries, no gaps."""
    log_path = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
    if not log_path.exists():
        return {"valid": True, "errors": []}
        
    errors = []
    with open(log_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                errors.append(f"Line {i}: empty line")
                continue
            try:
                entry = json.loads(line)
                required = ["entry_id", "timestamp_utc", "domain", "action_proposed",
                           "screening_result", "gate_result", "execution_result",
                           "real_outcome", "reasoning_summary", "credential_used"]
                for field in required:
                    if field not in entry:
                        errors.append(f"Line {i}: missing field '{field}'")
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: JSON decode error - {e}")
                
    return {"valid": len(errors) == 0, "errors": errors}

def get_recent_entries(domain: Optional[str] = None, count: int = 50) -> List[Dict]:
    """Get most recent entries for dashboard."""
    return read_audit_log(domain=domain, limit=count)

def search_audit(query: str, domain: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """Search audit log by text query."""
    log_path = Path(__file__).resolve().parent.parent / ".jarvis" / "audit_log.jsonl"
    if not log_path.exists():
        return []
        
    results = []
    query_lower = query.lower()
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if domain and entry.get("domain") != domain:
                    continue
                # Search in action, reasoning, outcome
                searchable = f"{entry.get('action_proposed','')} {entry.get('reasoning_summary','')} {entry.get('real_outcome','')}".lower()
                if query_lower in searchable:
                    results.append(entry)
                    if len(results) >= limit:
                        break
            except json.JSONDecodeError:
                continue
    return results
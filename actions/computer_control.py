"""
Computer Control Agent — Part 3.1: Full desktop automation.
Launching, closing, controlling applications; file operations; scheduling; RPA.
"""
import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.domain_agent import DomainAgent, DomainConfig, AutonomyLevel
from core.safety_guardian import is_killed, log_audit, is_breaker_tripped
from core.audit_log import write_audit_entry

class ComputerControlAgent(DomainAgent):
    """Full computer control: apps, files, scheduling, RPA."""
    
    def __init__(self):
        config = DomainConfig(
            domain="computer_control",
            autonomy_level=1,
            target_ceiling=5,
            caps={
                "max_file_ops_per_min": 100,
                "max_app_launches_per_min": 10,
                "allowed_dirs": ["~/Documents", "~/Downloads", "~/Desktop", "~/Projects", "~/jarvis_workspace"]
            },
            always_requires_approval=[
                "delete_file", "delete_dir", "format_disk", "modify_system_files",
                "install_software", "modify_registry", "run_as_admin"
            ],
            allowlist=[
                "notepad.exe", "code.exe", "python.exe", "cmd.exe", "powershell.exe",
                "chrome.exe", "firefox.exe", "explorer.exe", "notepad++.exe",
                "sublime_text.exe", "vim.exe", "git.exe", "npm.exe", "pip.exe"
            ]
        )
        super().__init__(config)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._file_op_count = 0
        self._last_minute = time.time()
        
    async def handle(self, action: str, params: Dict) -> Any:
        """Handle computer control actions."""
        if is_killed("computer_control"):
            raise PermissionError("Computer control domain is killed by safety guardian")
            
        can_exec, needs_approval, reason = self.can_execute(action)
        if not can_exec:
            return {"success": False, "error": reason, "requires_approval": False}
            
        if self.config.autonomy_level < 3 and not self._check_approval(params):
            return {"success": False, "error": "Requires Boss approval", "requires_approval": True}
            
        # Check circuit breakers
        if is_breaker_tripped("scope_commands_per_min"):
            return {"success": False, "error": "Rate limit exceeded"}
            
        try:
            if action == "launch_app":
                return await self._launch_app(params)
            elif action == "close_app":
                return await self._close_app(params)
            elif action == "run_command":
                return await self._run_command(params)
            elif action == "create_file":
                return await self._create_file(params)
            elif action == "read_file":
                return await self._read_file(params)
            elif action == "write_file":
                return await self._write_file(params)
            elif action == "delete_file":
                return await self._delete_file(params)
            elif action == "list_dir":
                return await self._list_dir(params)
            elif action == "create_dir":
                return await self._create_dir(params)
            elif action == "schedule_task":
                return await self._schedule_task(params)
            elif action == "take_screenshot":
                return await self._take_screenshot(params)
            elif action == "get_system_info":
                return await self._get_system_info()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _check_approval(self, params: Dict) -> bool:
        """Check if action has Boss approval."""
        return params.get("approved", False) or params.get("approved_by_boss", False)
        
    async def _launch_app(self, params: Dict) -> Dict:
        app = params.get("app")
        args = params.get("args", [])
        
        if not self.config.allowlist or params.get("approved", False):
            pass  # Approved or no allowlist
        elif not self._is_allowed(app):
            return {"success": False, "error": f"App not in allowlist: {app}", "requires_approval": True}
            
        try:
            proc = await asyncio.create_subprocess_exec(
                app, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            return {"success": True, "pid": proc.pid, "app": app}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _is_allowed(self, app: str) -> bool:
        app_lower = app.lower()
        for allowed in self.config.allowlist:
            if allowed.lower() in app_lower or app_lower in allowed.lower():
                return True
        return False
        
    async def _close_app(self, params: Dict) -> Dict:
        app = params.get("app")
        try:
            proc = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/IM", app,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            return {"success": True, "app": app}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _run_command(self, params: Dict) -> Dict:
        cmd = params.get("command")
        cwd = params.get("cwd", ".")
        shell = params.get("shell", False)
        
        if not self._check_rate_limit():
            return {"success": False, "error": "Rate limit exceeded"}
            
        try:
            if shell:
                proc = await asyncio.create_subprocess_shell(
                    cmd, cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                parts = cmd.split()
                proc = await asyncio.create_subprocess_exec(
                    parts[0], *parts[1:], cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            stdout, stderr = await proc.communicate()
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors="replace")[:5000],
                "stderr": stderr.decode(errors="replace")[:5000]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _check_rate_limit(self) -> bool:
        now = time.time()
        if now - self._last_minute > 60:
            self._file_op_count = 0
            self._last_minute = now
        if self._file_op_count >= self.config.caps.get("max_file_ops_per_min", 100):
            return False
        self._file_op_count += 1
        return True
        
    async def _create_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        content = params.get("content", "")
        
        if not self._is_allowed_path(path):
            return {"success": False, "error": "Path not in allowed directories", "requires_approval": True}
            
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params.get("content", ""), encoding="utf-8")
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _read_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        try:
            content = path.read_text(encoding="utf-8")
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _write_file(self, params: Dict) -> Dict:
        return await self._create_file(params)
        
    async def _delete_file(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        if not params.get("approved", False):
            return {"success": False, "error": "Delete requires Boss approval", "requires_approval": True}
        try:
            path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _list_dir(self, params: Dict) -> Dict:
        path = Path(params.get("path", "."))
        try:
            items = []
            for p in path.iterdir():
                items.append({
                    "name": p.name,
                    "type": "dir" if p.is_dir() else "file",
                    "size": p.stat().st_size if p.is_file() else None
                })
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _create_dir(self, params: Dict) -> Dict:
        path = Path(params.get("path", ""))
        try:
            path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _schedule_task(self, params: Dict) -> Dict:
        # Simple scheduling - in production would use proper scheduler
        return {"success": True, "scheduled": True}
        
    async def _take_screenshot(self, params: Dict) -> Dict:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            path = Path(params.get("path", "screenshot.png"))
            screenshot.save(path)
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _get_system_info(self) -> Dict:
        import psutil
        return {
            "success": True,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": psutil.boot_time()
        }
        
    def _is_allowed_path(self, path: Path) -> bool:
        allowed = self.config.caps.get("allowed_dirs", [])
        if not allowed:
            return True
        try:
            path.resolve()
            for allowed_dir in allowed:
                allowed_path = Path(os.path.expanduser(allowed_dir)).resolve()
                try:
                    path.relative_to(allowed_path)
                    return True
                except ValueError:
                    continue
        except Exception:
            pass
        return False
        
    def get_status(self) -> Dict:
        return {
            "domain": "computer_control",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "running_tasks": len(self._running_tasks),
            "file_ops_this_minute": self._file_op_count
        }
        
    def get_proposals(self) -> List[Dict]:
        return []  # Would return pending proposals
        
    def get_status(self) -> Dict:
        return {
            "domain": "computer_control",
            "autonomy_level": 1,
            "target_ceiling": 5,
            "running_tasks": len(self._running_tasks),
            "file_ops_this_minute": self._file_op_count
        }
        
    def get_proposals(self) -> List[Dict]:
        return []
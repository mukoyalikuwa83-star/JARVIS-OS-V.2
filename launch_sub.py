"""Launch JARVIS with subprocess for proper output capture."""
import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env["JARVIS_AUTO_START"] = "1"
log = open(".jarvis/crash_subprocess.log", "w", encoding="utf-8")
print("Launching JARVIS via subprocess...", file=log, flush=True)
proc = subprocess.Popen(
    [sys.executable, "main.py"],
    stdout=log, stderr=log,
    env=env, cwd=os.getcwd()
)
print(f"JARVIS PID: {proc.pid}", file=log, flush=True)
try:
    proc.wait(timeout=120)
    print(f"JARVIS exited with code: {proc.returncode}", file=log, flush=True)
except subprocess.TimeoutExpired:
    print("JARVIS still running after 120s (normal)", file=log, flush=True)
except Exception as e:
    print(f"Error: {e}", file=log, flush=True)
finally:
    log.close()

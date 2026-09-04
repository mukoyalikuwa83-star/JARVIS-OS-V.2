"""Launch JARVIS and capture ALL output to file."""
import subprocess, sys, os, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env["JARVIS_AUTO_START"] = "1"

log_path = ".jarvis\\full_crash.log"
print(f"Launching JARVIS, logging to {log_path}", flush=True)

while True:
    log = open(log_path, "a", encoding="utf-8")
    log.write(f"\n{'='*60}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting JARVIS\n{'='*60}\n")
    log.flush()
    
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=log, stderr=log,
        env=env, cwd=os.getcwd()
    )
    print(f"JARVIS PID: {proc.pid}", flush=True)
    
    rc = proc.wait()
    log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] JARVIS exited code {rc}\n")
    log.flush()
    log.close()
    
    print(f"JARVIS exited code {rc}, restarting in 3s...", flush=True)
    time.sleep(3)

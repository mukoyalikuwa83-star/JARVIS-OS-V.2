"""Launch JARVIS with full error capture."""
import sys, os, traceback
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["JARVIS_AUTO_START"] = "1"
sys.stdout = open(".jarvis/crash_full.log", "w", encoding="utf-8")
sys.stderr = sys.stdout
print("Starting JARVIS...", flush=True)
try:
    exec(open("main.py", encoding="utf-8").read())
except Exception as e:
    print(f"\nFATAL ERROR: {e}", flush=True)
    traceback.print_exc()
finally:
    print("\nJARVIS exited.", flush=True)
    sys.stdout.close()

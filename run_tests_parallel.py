import subprocess, sys, os

PYTHON = r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main\.venv\Scripts\python.exe'
BASE = r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main'
TIMEOUT = 25

test_files = [
    'tests/test_qa_system.py',
    'tests/test_deep_research.py',
    'tests/test_presentation_maker.py',
    'tests/test_startup_clap.py',
    'tests/test_desktop_integration.py',
    'tests/test_infinite_loop_detector.py',
    'tests/test_research_body.py',
]

results = {}
for f in test_files:
    full = os.path.join(BASE, f)
    if not os.path.exists(full):
        results[f] = "NOT FOUND"
        print(f"\n>>> {f} ... SKIPPED (not found)")
        continue

    print(f"\n>>> Running {f} ...")
    try:
        proc = subprocess.run(
            [PYTHON, full],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
        )
        stdout = proc.stdout
        stderr = proc.stderr

        output = (stdout + "\n" + stderr).strip()
        lines = output.split('\n')
        if len(lines) > 40:
            print(f"  ... ({len(lines) - 40} lines truncated)")
            for line in lines[:10]:
                print(f"  {line}")
            print(f"  ...")
            for line in lines[-10:]:
                print(f"  {line}")
        else:
            for line in lines:
                print(f"  {line}")

        results[f] = f"EXIT CODE: {proc.returncode}"
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {TIMEOUT}s - process killed")
        results[f] = "TIMEOUT (HUNG)"
    except Exception as e:
        print(f"  ERROR: {e}")
        results[f] = f"ERROR: {e}"

print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
for f, r in results.items():
    if r == "NOT FOUND":
        icon = "SKIP"
    elif "TIMEOUT" in r:
        icon = "HANG"
    elif "EXIT CODE: 0" in r:
        icon = "PASS"
    elif "EXIT CODE: 1" in r:
        icon = "FAIL"
    else:
        icon = "ERR"
    print(f"  [{icon}] {f}: {r}")

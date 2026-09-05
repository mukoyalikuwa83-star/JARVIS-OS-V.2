import subprocess
r1 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "add", "-A"], capture_output=True, text=True, timeout=30)
r2 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "commit", "-m", "Fix import hangs: defer sounddevice, remove ui import from awareness"], capture_output=True, text=True, timeout=30)
print(r2.stdout[:200])
r3 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
print("PUSH:", r3.returncode)

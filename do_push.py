import subprocess
r1 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "add", "-A"], capture_output=True, text=True, timeout=30)
r2 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "commit", "-m", "Final cleanup"], capture_output=True, text=True, timeout=30)
r3 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
print("Done:", r3.returncode)

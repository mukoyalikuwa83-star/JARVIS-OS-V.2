import subprocess
# Add all files
r1 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "add", "-A"], capture_output=True, text=True, timeout=30)
print("ADD:", r1.returncode)

# Commit
msg = "JARVIS-OS V.2: 76 tools, Stripe payments, persistent memory, latency fixes"
r2 = subprocess.run([r"C:\Program Files\Git\cmd\git.exe", "commit", "-m", msg], capture_output=True, text=True, timeout=30)
print("COMMIT:", r2.returncode)
print(r2.stdout[-500:] if r2.stdout else "")
print(r2.stderr[-500:] if r2.stderr else "")

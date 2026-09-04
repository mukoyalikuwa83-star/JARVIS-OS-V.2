$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$s = $ws.CreateShortcut("$desktop\JARVIS-OS V.2.lnk")
$s.TargetPath = "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main\JARVIS.bat"
$s.WorkingDirectory = "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
$s.Description = "JARVIS-OS V.2 AI Assistant"
$s.Save()
Write-Host "Desktop shortcut updated"
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$s2 = $ws.CreateShortcut("$startup\JARVIS-OS V.2.lnk")
$s2.TargetPath = "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main\JARVIS.bat"
$s2.WorkingDirectory = "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
$s2.Description = "JARVIS-OS V.2 AI Assistant"
$s2.Save()
Write-Host "Startup shortcut updated"
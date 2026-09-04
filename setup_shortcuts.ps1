$ws = New-Object -ComObject WScript.Shell
$desktop = "$env:USERPROFILE\Desktop"
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$target = "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main\JARVIS.bat"

$s = $ws.CreateShortcut("$desktop\JARVIS-OS V.2.lnk")
$s.TargetPath = $target
$s.Save()

$s2 = $ws.CreateShortcut("$startup\JARVIS-OS V.2.lnk")
$s2.TargetPath = $target
$s2.Save()

Write-Output "Shortcuts created successfully"

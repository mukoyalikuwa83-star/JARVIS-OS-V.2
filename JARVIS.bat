@echo off
title JARVIS-OS V.2
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"

:restart
if exist ".jarvis\.stop" del ".jarvis\.stop"
echo [%date% %time%] Starting JARVIS-OS V.2...
set JARVIS_AUTO_START=1
".venv\Scripts\python.exe" main.py
echo [%date% %time%] JARVIS exited. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto restart

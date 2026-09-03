@echo off
title JARVIS-OS V.2 - AI Assistant
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
set JARVIS_AUTO_START=1
:restart
echo [%date% %time%] Starting JARVIS-OS V.2...
".venv\Scripts\python.exe" main.py
echo [%date% %time%] JARVIS exited with code %ERRORLEVEL%
if exist .jarvis\.stop (
    echo Intentional shutdown detected. Stopping.
    del /f /q .jarvis\.stop >nul 2>&1
    exit /b
)
echo Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto restart

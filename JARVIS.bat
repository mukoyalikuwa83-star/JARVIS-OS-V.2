@echo off
title JARVIS-OS V.2 - AI Assistant
cd /d "C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main"
set JARVIS_AUTO_START=1
echo Starting JARVIS-OS V.2...
".venv\Scripts\python.exe" main.py
:loop
if exist .jarvis\.stop exit /b
timeout /t 3 /nobreak >nul
goto loop

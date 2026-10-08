@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe goto setup_needed
if not exist frontend-github\dist\index.html goto setup_needed
echo DataFlow Hub will be available at http://localhost:5000
echo Keep this terminal open. Press Ctrl+C to stop.
.venv\Scripts\python.exe script\app.py
pause
exit /b
:setup_needed
echo Run Setup_Windows.bat first.
pause

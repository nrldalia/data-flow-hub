@echo off
cd /d "%~dp0"
echo DataFlow V1.2.0 - http://127.0.0.1:5000
echo Keep this window open. Close the old DataFlow server before starting.
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe script\app.py --open-browser
) else (
  set "PYTHONPATH=%~dp0..\..\work\python-packages"
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" script\app.py --open-browser
)
pause

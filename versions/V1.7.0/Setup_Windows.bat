@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 goto python_missing
where npm.cmd >nul 2>&1
if errorlevel 1 goto node_missing
if not exist .venv\Scripts\python.exe py -m venv .venv
.venv\Scripts\python.exe -m pip install -r script\requirements.txt
if errorlevel 1 goto failed
cd frontend-github
call npm.cmd ci
if errorlevel 1 goto failed
call npm.cmd run build
if errorlevel 1 goto failed
cd ..
echo Setup complete. Run Start_V1.7.0.bat next.
pause
exit /b 0
:python_missing
echo Install Python 3.11 or 3.12 with Add Python to PATH selected.
pause
exit /b 1
:node_missing
echo Install Node.js 20.19+ or 22.12+ first. Reopen this launcher after installation.
pause
exit /b 1
:failed
echo Setup failed. Review the error above and check your internet connection.
pause
exit /b 1

@echo off
setlocal
title DataFlow - Localhost
set "APP_DIR=%~dp0V1.4.A2"
if not exist "%APP_DIR%\script\app.py" set "APP_DIR=%~dp0..\V1.4.A2"
if not exist "%APP_DIR%\script\app.py" goto missing
cd /d "%APP_DIR%"
set "DATAFLOW_PORT=5001"
powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:5001/api/v1/health' -TimeoutSec 2; if ($r.version -eq '1.4.A2') { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 goto already_running
if exist ".venv\Scripts\python.exe" goto local_python
set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHONPATH=%APP_DIR%\..\..\work\python-packages"
if exist "%PYTHON_EXE%" if exist "%PYTHONPATH%\flask" if exist "frontend-github\dist\index.html" goto start
echo Preparing DataFlow for first use...
call Setup_Windows.bat
if errorlevel 1 goto failed
cd /d "%APP_DIR%"
:local_python
set "PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" goto failed
if not exist "frontend-github\dist\index.html" goto failed
:start
echo Opening http://127.0.0.1:5001/
echo Keep this window open while using DataFlow.
"%PYTHON_EXE%" script\app.py --open-browser
echo.
echo DataFlow has stopped.
pause
exit /b
:already_running
start "" "http://127.0.0.1:5001/"
exit /b
:missing
echo Cannot find the V1.4.A2 application beside this launcher.
pause
exit /b 1
:failed
echo Setup did not complete. Review the message above.
pause
exit /b 1

@echo off
rem IP Stability Monitor - Windows launcher (one click)
rem First run: creates a virtual environment, installs dependencies and a starter
rem config.json, then starts the monitor and opens the dashboard in your browser.
rem Restarts triggered from the dashboard are handled automatically.
setlocal
cd /d "%~dp0"
title IP Stability Monitor

if not exist venv\Scripts\python.exe (
  echo Creating virtual environment...
  py -3 -m venv venv 2>nul || python -m venv venv
  if not exist venv\Scripts\python.exe (
    echo Python 3.9+ is required. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
  )
)
echo Checking requirements...
venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo Could not install requirements. Check the internet connection and try again.
  pause
  exit /b 1
)

rem Open the dashboard once the server has had a few seconds to start.
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start "" http://localhost:8096/"

set IPMON_SUPERVISED=1
:run
venv\Scripts\python.exe app.py
if %ERRORLEVEL%==3 (
  echo Restarting monitor...
  goto run
)
echo Monitor stopped (exit code %ERRORLEVEL%).
pause

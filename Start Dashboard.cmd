@echo off
rem Starts the whole app: sets up Python and the React client on first run, then
rem serves the dashboard at http://127.0.0.1:8010 with the scheduler and agents.
rem If an older copy is already running (and idle) it is restarted, so a double-click
rem always opens the newest version. Pass --restart to force that, --no-browser to
rem start without opening a tab. Keep this window open; closing it stops the app.
setlocal
title Career Workspace
cd /d "%~dp0career-dashboard\backend"

echo Starting the Career Workspace (every profile)...
echo The first start installs everything and can take a few minutes.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Setting up Python...
  py -3.12 -m venv .venv || goto :error
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, yaml, pypdf, PIL, tzdata, langchain, langgraph" >nul 2>&1
if errorlevel 1 (
  echo [2/3] Installing Python packages...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)

if not exist "..\frontend\node_modules\vite\bin\vite.js" (
  echo [3/3] Installing the dashboard's web packages...
  pushd "..\frontend"
  call npm.cmd ci || (popd & goto :error)
  popd
)

".venv\Scripts\python.exe" run.py %*
exit /b %errorlevel%

:error
echo.
echo Dashboard setup failed. Keep this window open and share the message above.
pause
exit /b 1

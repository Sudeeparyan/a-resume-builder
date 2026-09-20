@echo off
setlocal
cd /d "%~dp0career-dashboard\backend"

if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv || goto :error
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, yaml, pypdf, PIL, tzdata, langchain, langgraph" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)

if not exist "..\frontend\node_modules\vite\bin\vite.js" (
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

@echo off
rem Annie's daily morning run — target of the "Annie Daily Job Search" scheduled task.
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "PY=%~dp0..\career-dashboard\backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0morning_run.py" %* >> "%~dp0logs\morning-run.log" 2>&1
exit /b %errorlevel%

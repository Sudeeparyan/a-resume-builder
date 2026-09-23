@echo off
rem Windows twin of "Check Workspace.command" (which is macOS-only: it uses
rem backend/.venv/bin and the macOS Tectonic wrapper). Runs the same checks:
rem backend tests, workspace + layout validators, frontend build, frontend tests.
setlocal
cd /d "%~dp0career-dashboard"
set "PY=backend\.venv\Scripts\python.exe"

"%PY%" -m pytest tests -q || goto :error
"%PY%" backend/scripts/validate_workspace.py || goto :error
"%PY%" backend/scripts/check_layout.py || goto :error
"%PY%" backend/scripts/build_frontend.py || goto :error
pushd frontend
call npm.cmd test || (popd & goto :error)
popd
echo.
echo All checks passed.
exit /b 0

:error
echo.
echo CHECKS FAILED — see the output above.
exit /b 1

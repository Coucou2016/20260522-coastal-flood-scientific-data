@echo off
setlocal
cd /d "%~dp0\.."

if "%~1"=="" (
  echo Usage: scripts\run_python_checked.cmd path\to\script.py [args...]
  exit /b 64
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH. Install Python or activate the project environment, then rerun the publication gate.
  exit /b 9009
)

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python %*
exit /b %ERRORLEVEL%

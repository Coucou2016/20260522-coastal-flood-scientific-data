@echo off
setlocal
cd /d "%~dp0\.."

if not exist requirements-publication.txt (
  echo Missing requirements-publication.txt.
  exit /b 66
)

call scripts\run_python_checked.cmd -m pip install -r requirements-publication.txt %*
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_archive_handoff.py %*
exit /b %ERRORLEVEL%

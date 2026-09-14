@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_submission_ready_terminal_run_record.py %*
exit /b %ERRORLEVEL%

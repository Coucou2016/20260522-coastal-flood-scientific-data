@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\record_submission_ready_terminal_run.py %*
exit /b %ERRORLEVEL%

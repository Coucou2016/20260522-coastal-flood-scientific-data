@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_submission_ready_failure_summary.py %*
exit /b %ERRORLEVEL%

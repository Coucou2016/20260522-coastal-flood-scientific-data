@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_final_submission_handoff_report.py %*
exit /b %ERRORLEVEL%

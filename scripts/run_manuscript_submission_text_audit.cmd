@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_manuscript_submission_text.py %*
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_submission_artifact_consistency.py %*
exit /b %ERRORLEVEL%

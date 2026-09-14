@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_journal_submission_metadata.py %*
exit /b %ERRORLEVEL%

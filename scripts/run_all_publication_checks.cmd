@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_final_submission_handoff.cmd %*
exit /b %ERRORLEVEL%

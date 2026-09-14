@echo off
setlocal
cd /d "%~dp0\.."

echo run_publication_gate_logged.cmd now delegates to the final submission handoff gate.
call scripts\run_final_submission_handoff.cmd %*
exit /b %ERRORLEVEL%

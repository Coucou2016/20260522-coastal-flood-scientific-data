@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_final_submission_handoff_evidence_bundle.py %*
exit /b %ERRORLEVEL%

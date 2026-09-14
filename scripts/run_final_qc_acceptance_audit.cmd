@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_final_qc_acceptance.py %*
exit /b %ERRORLEVEL%

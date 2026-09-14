@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_final_evidence_index.py %*
exit /b %ERRORLEVEL%

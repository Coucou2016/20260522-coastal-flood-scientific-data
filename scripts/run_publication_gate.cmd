@echo off
setlocal
cd /d "%~dp0\.."
call scripts\diagnose_publication_environment.cmd
call scripts\run_python_checked.cmd scripts\publication_gate.py %*
exit /b %ERRORLEVEL%

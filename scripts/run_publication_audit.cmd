@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_publication_readiness.py %*
exit /b %ERRORLEVEL%

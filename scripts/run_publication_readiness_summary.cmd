@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_publication_readiness_summary.py %*
exit /b %ERRORLEVEL%

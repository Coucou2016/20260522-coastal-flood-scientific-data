@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_python_runtime_dependencies.py %*
exit /b %ERRORLEVEL%

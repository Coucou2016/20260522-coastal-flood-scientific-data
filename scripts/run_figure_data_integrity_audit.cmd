@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_figure_data_integrity.py %*
exit /b %ERRORLEVEL%

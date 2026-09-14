@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_figure_visual_quality.py %*
exit /b %ERRORLEVEL%

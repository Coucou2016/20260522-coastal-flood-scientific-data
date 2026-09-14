@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_manuscript_figure_inventory.py %*
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_manual_figure_review_sheet.py %*
exit /b %ERRORLEVEL%

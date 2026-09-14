@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_final_figure_data_issue_register.py %*
exit /b %ERRORLEVEL%

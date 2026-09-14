@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\audit_final_figure_data_review_matrix.py %*
exit /b %ERRORLEVEL%

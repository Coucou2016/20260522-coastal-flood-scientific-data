@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\build_final_figure_data_review_matrix_template.py %*
exit /b %ERRORLEVEL%

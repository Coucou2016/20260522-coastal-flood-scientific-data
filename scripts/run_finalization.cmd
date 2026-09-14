@echo off
setlocal
cd /d "%~dp0\.."
call scripts\run_python_checked.cmd scripts\finalize_cee_publication_package.py %*
exit /b %ERRORLEVEL%

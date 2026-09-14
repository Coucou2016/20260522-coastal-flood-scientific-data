@echo off
setlocal
cd /d "%~dp0\.."
python scripts\run_major_revision_rebuild.py %*
exit /b %ERRORLEVEL%

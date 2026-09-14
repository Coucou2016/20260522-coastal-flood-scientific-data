@echo off
setlocal
cd /d "%~dp0\.."

if not exist logs mkdir logs
set "LOG=logs\publication_environment_diagnostics.txt"

> "%LOG%" echo Publication Environment Diagnostics
>> "%LOG%" echo ===================================
>> "%LOG%" echo.
>> "%LOG%" echo Diagnostic-only log. This file does not prove publication readiness.
>> "%LOG%" echo Publication readiness still requires scripts\run_publication_gate.cmd to finish with Passed: True.
>> "%LOG%" echo.
>> "%LOG%" echo Date: %DATE%
>> "%LOG%" echo Time: %TIME%
>> "%LOG%" echo Working directory: %CD%
>> "%LOG%" echo.

>> "%LOG%" echo Python on PATH:
where python >> "%LOG%" 2>&1
>> "%LOG%" echo Exit code: %ERRORLEVEL%
>> "%LOG%" echo.

>> "%LOG%" echo Python version:
python --version >> "%LOG%" 2>&1
>> "%LOG%" echo Exit code: %ERRORLEVEL%
>> "%LOG%" echo.

>> "%LOG%" echo pip version:
python -m pip --version >> "%LOG%" 2>&1
>> "%LOG%" echo Exit code: %ERRORLEVEL%
>> "%LOG%" echo.

>> "%LOG%" echo Required files:
if exist requirements-publication.txt (>> "%LOG%" echo OK requirements-publication.txt) else (>> "%LOG%" echo MISSING requirements-publication.txt)
if exist scripts\run_python_checked.cmd (>> "%LOG%" echo OK scripts\run_python_checked.cmd) else (>> "%LOG%" echo MISSING scripts\run_python_checked.cmd)
if exist scripts\install_publication_requirements.cmd (>> "%LOG%" echo OK scripts\install_publication_requirements.cmd) else (>> "%LOG%" echo MISSING scripts\install_publication_requirements.cmd)
if exist scripts\run_publication_gate.cmd (>> "%LOG%" echo OK scripts\run_publication_gate.cmd) else (>> "%LOG%" echo MISSING scripts\run_publication_gate.cmd)
if exist scripts\publication_gate.py (>> "%LOG%" echo OK scripts\publication_gate.py) else (>> "%LOG%" echo MISSING scripts\publication_gate.py)
if exist manuscript\process_terrain_coastal_flood_CEE_manuscript.md (>> "%LOG%" echo OK manuscript\process_terrain_coastal_flood_CEE_manuscript.md) else (>> "%LOG%" echo MISSING manuscript\process_terrain_coastal_flood_CEE_manuscript.md)
if exist manuscript\process_terrain_coastal_flood_CEE_manuscript_review.html (>> "%LOG%" echo OK manuscript\process_terrain_coastal_flood_CEE_manuscript_review.html) else (>> "%LOG%" echo MISSING manuscript\process_terrain_coastal_flood_CEE_manuscript_review.html)

>> "%LOG%" echo.
>> "%LOG%" echo Suggested next commands:
>> "%LOG%" echo scripts\install_publication_requirements.cmd
>> "%LOG%" echo scripts\run_publication_gate.cmd

type "%LOG%"
exit /b 0

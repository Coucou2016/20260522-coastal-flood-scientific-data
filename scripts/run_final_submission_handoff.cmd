@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."

if not exist logs mkdir logs

set "STAMP=%DATE%_%TIME%"
set "STAMP=%STAMP::=-%"
set "STAMP=%STAMP:/=-%"
set "STAMP=%STAMP:\=-%"
set "STAMP=%STAMP: =_%"
set "STAMP=%STAMP:.=-%"
set "LOG=logs\final_submission_handoff_%STAMP%.log"
set "LATEST=logs\final_submission_handoff_latest.log"

echo Writing final submission handoff log to %LOG%
echo Final submission handoff started at %DATE% %TIME% > "%LOG%"
echo Working directory: %CD% >> "%LOG%"
echo Command: scripts\run_final_submission_handoff.cmd %* >> "%LOG%"
echo. >> "%LOG%"

echo Running submission-ready gate >> "%LOG%"
call scripts\run_submission_ready_gate.cmd %* >> "%LOG%" 2>&1
set "GATE_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Recording successful terminal run >> "%LOG%"
if "!GATE_STATUS!"=="0" (
    call scripts\record_submission_ready_terminal_run.cmd >> "%LOG%" 2>&1
    set "RECORD_STATUS=!ERRORLEVEL!"
) else (
    echo Skipping terminal-run record because submission-ready gate failed. >> "%LOG%"
    set "RECORD_STATUS=1"
)

echo. >> "%LOG%"
echo Auditing terminal-run record >> "%LOG%"
set "RECORD_AUDIT_STATUS=1"
if "!GATE_STATUS!"=="0" (
    if "!RECORD_STATUS!"=="0" (
        call scripts\run_submission_ready_terminal_run_record_audit.cmd >> "%LOG%" 2>&1
        set "RECORD_AUDIT_STATUS=!ERRORLEVEL!"
    ) else (
        echo Skipping terminal-run record audit because terminal-run record failed. >> "%LOG%"
    )
) else (
    echo Skipping terminal-run record audit because submission-ready gate failed. >> "%LOG%"
)

set "FINAL_HANDOFF_GATE_EXIT_CODE=%GATE_STATUS%"
set "FINAL_HANDOFF_RECORD_EXIT_CODE=%RECORD_STATUS%"
set "FINAL_HANDOFF_RECORD_AUDIT_EXIT_CODE=%RECORD_AUDIT_STATUS%"
set "FINAL_HANDOFF_LOG=%LOG%"

echo. >> "%LOG%"
echo Building final submission handoff evidence bundle >> "%LOG%"
set "HANDOFF_EVIDENCE_STATUS=1"
if "!GATE_STATUS!"=="0" (
    if "!RECORD_STATUS!"=="0" (
        if "!RECORD_AUDIT_STATUS!"=="0" (
            call scripts\build_final_submission_handoff_evidence_bundle.cmd >> "%LOG%" 2>&1
            set "HANDOFF_EVIDENCE_STATUS=!ERRORLEVEL!"
        ) else (
            echo Skipping final handoff evidence bundle because terminal-run record audit failed. >> "%LOG%"
        )
    ) else (
        echo Skipping final handoff evidence bundle because terminal-run record failed. >> "%LOG%"
    )
) else (
    echo Skipping final handoff evidence bundle because submission-ready gate failed. >> "%LOG%"
)

echo. >> "%LOG%"
echo Auditing final submission handoff evidence bundle >> "%LOG%"
set "HANDOFF_EVIDENCE_AUDIT_STATUS=1"
if "!HANDOFF_EVIDENCE_STATUS!"=="0" (
    call scripts\run_final_submission_handoff_evidence_bundle_audit.cmd >> "%LOG%" 2>&1
    set "HANDOFF_EVIDENCE_AUDIT_STATUS=!ERRORLEVEL!"
) else (
    echo Skipping final handoff evidence bundle audit because bundle generation failed or was skipped. >> "%LOG%"
)

set "FINAL_HANDOFF_EVIDENCE_EXIT_CODE=%HANDOFF_EVIDENCE_STATUS%"
set "FINAL_HANDOFF_EVIDENCE_AUDIT_EXIT_CODE=%HANDOFF_EVIDENCE_AUDIT_STATUS%"

echo. >> "%LOG%"
echo Building final submission handoff report >> "%LOG%"
call scripts\build_final_submission_handoff_report.cmd >> "%LOG%" 2>&1
set "HANDOFF_REPORT_STATUS=%ERRORLEVEL%"

set "STATUS=0"
if not "%GATE_STATUS%"=="0" set "STATUS=%GATE_STATUS%"
if "%STATUS%"=="0" if not "%RECORD_STATUS%"=="0" set "STATUS=%RECORD_STATUS%"
if "%STATUS%"=="0" if not "%RECORD_AUDIT_STATUS%"=="0" set "STATUS=%RECORD_AUDIT_STATUS%"
if "%STATUS%"=="0" if not "%HANDOFF_EVIDENCE_STATUS%"=="0" set "STATUS=%HANDOFF_EVIDENCE_STATUS%"
if "%STATUS%"=="0" if not "%HANDOFF_EVIDENCE_AUDIT_STATUS%"=="0" set "STATUS=%HANDOFF_EVIDENCE_AUDIT_STATUS%"
if "%STATUS%"=="0" if not "%HANDOFF_REPORT_STATUS%"=="0" set "STATUS=%HANDOFF_REPORT_STATUS%"

echo. >> "%LOG%"
echo Final submission handoff finished at %DATE% %TIME% with exit code %STATUS% >> "%LOG%"
echo Submission-ready gate exit code: %GATE_STATUS% >> "%LOG%"
echo Terminal-run record exit code: %RECORD_STATUS% >> "%LOG%"
echo Terminal-run record audit exit code: %RECORD_AUDIT_STATUS% >> "%LOG%"
echo Final submission handoff evidence bundle exit code: %HANDOFF_EVIDENCE_STATUS% >> "%LOG%"
echo Final submission handoff evidence bundle audit exit code: %HANDOFF_EVIDENCE_AUDIT_STATUS% >> "%LOG%"
echo Final submission handoff report exit code: %HANDOFF_REPORT_STATUS% >> "%LOG%"

copy /Y "%LOG%" "%LATEST%" > nul

type "%LOG%"
exit /b %STATUS%

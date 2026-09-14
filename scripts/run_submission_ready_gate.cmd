@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

if not exist logs mkdir logs

set "STAMP=%DATE%_%TIME%"
set "STAMP=%STAMP::=-%"
set "STAMP=%STAMP:/=-%"
set "STAMP=%STAMP:\=-%"
set "STAMP=%STAMP: =_%"
set "STAMP=%STAMP:.=-%"
set "LOG=logs\submission_ready_gate_%STAMP%.log"
set "LATEST=logs\submission_ready_gate_latest.log"

echo Writing submission-ready gate log to %LOG%
echo Submission-ready gate started at %DATE% %TIME% > "%LOG%"
echo Working directory: %CD% >> "%LOG%"
echo Command: scripts\run_submission_ready_gate.cmd %* >> "%LOG%"
echo. >> "%LOG%"

echo Auditing submission-ready gate scripts >> "%LOG%"
call scripts\run_submission_ready_gate_scripts_audit.cmd >> "%LOG%" 2>&1
set "SCRIPT_AUDIT_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Running core publication gate >> "%LOG%"
call scripts\run_publication_gate.cmd %* >> "%LOG%" 2>&1
set "CORE_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Building final figure/data review matrix template >> "%LOG%"
call scripts\build_final_figure_data_review_matrix_template.cmd >> "%LOG%" 2>&1
set "REVIEW_MATRIX_TEMPLATE_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Running final figure/data review matrix audit >> "%LOG%"
call scripts\run_final_figure_data_review_matrix_audit.cmd >> "%LOG%" 2>&1
set "REVIEW_MATRIX_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Running final figure/data issue register audit >> "%LOG%"
call scripts\run_final_figure_data_issue_register_audit.cmd >> "%LOG%" 2>&1
set "ISSUE_REGISTER_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Running final figure/data sign-off audit >> "%LOG%"
call scripts\run_final_figure_data_signoff_audit.cmd >> "%LOG%" 2>&1
set "SIGNOFF_STATUS=%ERRORLEVEL%"

set "CORE_GATE_EXIT_CODE=%CORE_STATUS%"
set "FIGURE_DATA_REVIEW_MATRIX_TEMPLATE_EXIT_CODE=%REVIEW_MATRIX_TEMPLATE_STATUS%"
set "FIGURE_DATA_REVIEW_MATRIX_EXIT_CODE=%REVIEW_MATRIX_STATUS%"
set "FIGURE_DATA_ISSUE_REGISTER_EXIT_CODE=%ISSUE_REGISTER_STATUS%"
set "FIGURE_DATA_SIGNOFF_EXIT_CODE=%SIGNOFF_STATUS%"
set "SUBMISSION_READY_SCRIPT_AUDIT_EXIT_CODE=%SCRIPT_AUDIT_STATUS%"
set "SUBMISSION_READY_LOG=%LOG%"

echo. >> "%LOG%"
echo Building submission-ready evidence bundle >> "%LOG%"
call scripts\build_submission_ready_evidence_bundle.cmd >> "%LOG%" 2>&1
set "EVIDENCE_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Auditing submission-ready evidence bundle >> "%LOG%"
call scripts\run_submission_ready_evidence_bundle_audit.cmd >> "%LOG%" 2>&1
set "EVIDENCE_AUDIT_STATUS=%ERRORLEVEL%"

set "SUBMISSION_READY_EVIDENCE_EXIT_CODE=%EVIDENCE_STATUS%"
set "SUBMISSION_READY_EVIDENCE_AUDIT_EXIT_CODE=%EVIDENCE_AUDIT_STATUS%"

echo. >> "%LOG%"
echo Building combined submission-ready report >> "%LOG%"
call scripts\run_python_checked.cmd scripts\build_submission_ready_report.py >> "%LOG%" 2>&1
set "REPORT_STATUS=%ERRORLEVEL%"

echo. >> "%LOG%"
echo Building submission-ready failure summary >> "%LOG%"
call scripts\build_submission_ready_failure_summary.cmd >> "%LOG%" 2>&1
set "FAILURE_SUMMARY_STATUS=%ERRORLEVEL%"

set "STATUS=0"
if not "%SCRIPT_AUDIT_STATUS%"=="0" set "STATUS=%SCRIPT_AUDIT_STATUS%"
if "%STATUS%"=="0" if not "%CORE_STATUS%"=="0" set "STATUS=%CORE_STATUS%"
if "%STATUS%"=="0" if not "%REVIEW_MATRIX_TEMPLATE_STATUS%"=="0" set "STATUS=%REVIEW_MATRIX_TEMPLATE_STATUS%"
if "%STATUS%"=="0" if not "%REVIEW_MATRIX_STATUS%"=="0" set "STATUS=%REVIEW_MATRIX_STATUS%"
if "%STATUS%"=="0" if not "%ISSUE_REGISTER_STATUS%"=="0" set "STATUS=%ISSUE_REGISTER_STATUS%"
if "%STATUS%"=="0" if not "%SIGNOFF_STATUS%"=="0" set "STATUS=%SIGNOFF_STATUS%"
if "%STATUS%"=="0" if not "%REPORT_STATUS%"=="0" set "STATUS=%REPORT_STATUS%"
if "%STATUS%"=="0" if not "%FAILURE_SUMMARY_STATUS%"=="0" set "STATUS=%FAILURE_SUMMARY_STATUS%"
if "%STATUS%"=="0" if not "%EVIDENCE_STATUS%"=="0" set "STATUS=%EVIDENCE_STATUS%"
if "%STATUS%"=="0" if not "%EVIDENCE_AUDIT_STATUS%"=="0" set "STATUS=%EVIDENCE_AUDIT_STATUS%"

echo. >> "%LOG%"
echo Submission-ready gate finished at %DATE% %TIME% with exit code %STATUS% >> "%LOG%"
echo Submission-ready gate scripts audit exit code: %SCRIPT_AUDIT_STATUS% >> "%LOG%"
echo Core publication gate exit code: %CORE_STATUS% >> "%LOG%"
echo Figure/data review matrix template exit code: %REVIEW_MATRIX_TEMPLATE_STATUS% >> "%LOG%"
echo Figure/data review matrix exit code: %REVIEW_MATRIX_STATUS% >> "%LOG%"
echo Figure/data issue register exit code: %ISSUE_REGISTER_STATUS% >> "%LOG%"
echo Figure/data sign-off exit code: %SIGNOFF_STATUS% >> "%LOG%"
echo Combined report exit code: %REPORT_STATUS% >> "%LOG%"
echo Submission-ready evidence bundle exit code: %EVIDENCE_STATUS% >> "%LOG%"
echo Submission-ready evidence bundle audit exit code: %EVIDENCE_AUDIT_STATUS% >> "%LOG%"
echo Submission-ready failure summary exit code: %FAILURE_SUMMARY_STATUS% >> "%LOG%"

copy /Y "%LOG%" "%LATEST%" > nul

type "%LOG%"
exit /b %STATUS%

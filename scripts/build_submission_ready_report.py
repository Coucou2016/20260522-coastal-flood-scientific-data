"""Build a combined final submission-readiness report.

This report is intentionally stricter than the core publication gate summary:
it requires the automated publication gate, the final figure/data sign-off
audit, and the expected evidence artifacts to agree before reporting that the
package is ready for journal submission.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"

REPORT_JSON = LOGS_DIR / "submission_ready_gate_report.json"
REPORT_MD = LOGS_DIR / "submission_ready_gate_report.md"

CORE_REPORT = LOGS_DIR / "publication_gate_report.json"
REVIEW_MATRIX_REPORT = LOGS_DIR / "final_figure_data_review_matrix_audit.json"
REVIEW_MATRIX_TEMPLATE_REPORT = LOGS_DIR / "final_figure_data_review_matrix_template.json"
SIGNOFF_REPORT = LOGS_DIR / "final_figure_data_signoff_audit.json"
ISSUE_REGISTER_REPORT = LOGS_DIR / "final_figure_data_issue_register_audit.json"
SCRIPT_AUDIT_REPORT = LOGS_DIR / "submission_ready_gate_scripts_audit.json"
EVIDENCE_BUNDLE_AUDIT_REPORT = LOGS_DIR / "submission_ready_evidence_bundle_audit.json"

REQUIRED_EVIDENCE = [
    LOGS_DIR / "publication_gate_report.md",
    LOGS_DIR / "publication_gate_report.json",
    LOGS_DIR / "submission_ready_gate_scripts_audit.md",
    LOGS_DIR / "submission_ready_gate_scripts_audit.json",
    LOGS_DIR / "final_figure_data_review_matrix_template.md",
    LOGS_DIR / "final_figure_data_review_matrix_template.json",
    LOGS_DIR / "final_figure_data_review_matrix_audit.md",
    LOGS_DIR / "final_figure_data_review_matrix_audit.json",
    LOGS_DIR / "final_figure_data_issue_register_audit.md",
    LOGS_DIR / "final_figure_data_issue_register_audit.json",
    LOGS_DIR / "final_figure_data_signoff_audit.md",
    LOGS_DIR / "final_figure_data_signoff_audit.json",
    ROOT / "publication_gate_evidence" / "evidence_manifest.json",
    ROOT / "publication_gate_evidence" / "evidence_manifest.sha256",
    ROOT / "submission_ready_gate_evidence" / "evidence_manifest.json",
    ROOT / "submission_ready_gate_evidence" / "evidence_manifest.sha256",
    LOGS_DIR / "submission_ready_evidence_bundle_audit.md",
    LOGS_DIR / "submission_ready_evidence_bundle_audit.json",
    ROOT / "publication_package.zip",
    ROOT / "final_archive_manifest.json",
    ROOT / "manuscript" / "final_figure_data_signoff.json",
]


def read_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"Missing JSON report: {path.relative_to(ROOT)}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON report {path.relative_to(ROOT)}: {exc}"
    if not isinstance(value, dict):
        return None, f"JSON report must contain an object: {path.relative_to(ROOT)}"
    return value, None


def bool_field(value: dict | None, *names: str) -> bool | None:
    if value is None:
        return None
    for name in names:
        candidate = value.get(name)
        if isinstance(candidate, bool):
            return candidate
        if isinstance(candidate, str) and candidate.lower() in {"true", "false"}:
            return candidate.lower() == "true"
    return None


def int_env(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def build_report() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    core_exit = int_env("CORE_GATE_EXIT_CODE")
    review_matrix_template_exit = int_env("FIGURE_DATA_REVIEW_MATRIX_TEMPLATE_EXIT_CODE")
    review_matrix_exit = int_env("FIGURE_DATA_REVIEW_MATRIX_EXIT_CODE")
    issue_register_exit = int_env("FIGURE_DATA_ISSUE_REGISTER_EXIT_CODE")
    signoff_exit = int_env("FIGURE_DATA_SIGNOFF_EXIT_CODE")
    script_audit_exit = int_env("SUBMISSION_READY_SCRIPT_AUDIT_EXIT_CODE")
    evidence_exit = int_env("SUBMISSION_READY_EVIDENCE_EXIT_CODE")
    evidence_audit_exit = int_env("SUBMISSION_READY_EVIDENCE_AUDIT_EXIT_CODE")
    log_path = os.environ.get("SUBMISSION_READY_LOG", "").strip()

    if script_audit_exit is None:
        errors.append("SUBMISSION_READY_SCRIPT_AUDIT_EXIT_CODE was not provided to the final report builder.")
    elif script_audit_exit != 0:
        errors.append(f"Submission-ready gate scripts audit exit code is {script_audit_exit}.")

    if core_exit is None:
        errors.append("CORE_GATE_EXIT_CODE was not provided to the final report builder.")
    elif core_exit != 0:
        errors.append(f"Core publication gate exit code is {core_exit}.")

    if review_matrix_template_exit is None:
        errors.append("FIGURE_DATA_REVIEW_MATRIX_TEMPLATE_EXIT_CODE was not provided to the final report builder.")
    elif review_matrix_template_exit != 0:
        errors.append(f"Final figure/data review matrix template exit code is {review_matrix_template_exit}.")

    if review_matrix_exit is None:
        errors.append("FIGURE_DATA_REVIEW_MATRIX_EXIT_CODE was not provided to the final report builder.")
    elif review_matrix_exit != 0:
        errors.append(f"Final figure/data review matrix audit exit code is {review_matrix_exit}.")

    if issue_register_exit is None:
        errors.append("FIGURE_DATA_ISSUE_REGISTER_EXIT_CODE was not provided to the final report builder.")
    elif issue_register_exit != 0:
        errors.append(f"Final figure/data issue register audit exit code is {issue_register_exit}.")

    if signoff_exit is None:
        errors.append("FIGURE_DATA_SIGNOFF_EXIT_CODE was not provided to the final report builder.")
    elif signoff_exit != 0:
        errors.append(f"Final figure/data sign-off audit exit code is {signoff_exit}.")

    if evidence_exit is None:
        errors.append("SUBMISSION_READY_EVIDENCE_EXIT_CODE was not provided to the final report builder.")
    elif evidence_exit != 0:
        errors.append(f"Submission-ready evidence bundle exit code is {evidence_exit}.")

    if evidence_audit_exit is None:
        errors.append("SUBMISSION_READY_EVIDENCE_AUDIT_EXIT_CODE was not provided to the final report builder.")
    elif evidence_audit_exit != 0:
        errors.append(f"Submission-ready evidence bundle audit exit code is {evidence_audit_exit}.")

    script_audit_report, script_audit_error = read_json(SCRIPT_AUDIT_REPORT)
    if script_audit_error:
        errors.append(script_audit_error)
    script_audit_passed = bool_field(script_audit_report, "passed", "Passed", "success")
    if script_audit_passed is not True:
        errors.append(f"Submission-ready gate scripts audit does not prove success: passed={script_audit_passed!r}.")

    core_report, core_error = read_json(CORE_REPORT)
    if core_error:
        errors.append(core_error)
    core_passed = bool_field(core_report, "passed", "Passed", "gate_passed", "success")
    if core_passed is not True:
        errors.append(f"Core publication gate report does not prove success: passed={core_passed!r}.")

    review_matrix_template_report, review_matrix_template_error = read_json(REVIEW_MATRIX_TEMPLATE_REPORT)
    if review_matrix_template_error:
        errors.append(review_matrix_template_error)
    review_matrix_template_passed = bool_field(review_matrix_template_report, "passed", "Passed", "success")
    if review_matrix_template_passed is not True:
        errors.append(
            f"Final figure/data review matrix template report does not prove success: "
            f"passed={review_matrix_template_passed!r}."
        )

    review_matrix_report, review_matrix_error = read_json(REVIEW_MATRIX_REPORT)
    if review_matrix_error:
        errors.append(review_matrix_error)
    review_matrix_passed = bool_field(review_matrix_report, "passed", "Passed", "success")
    if review_matrix_passed is not True:
        errors.append(f"Final figure/data review matrix audit does not prove success: passed={review_matrix_passed!r}.")

    issue_register_report, issue_register_error = read_json(ISSUE_REGISTER_REPORT)
    if issue_register_error:
        errors.append(issue_register_error)
    issue_register_passed = bool_field(issue_register_report, "passed", "Passed", "success")
    if issue_register_passed is not True:
        errors.append(f"Final figure/data issue register audit does not prove success: passed={issue_register_passed!r}.")

    signoff_report, signoff_error = read_json(SIGNOFF_REPORT)
    if signoff_error:
        errors.append(signoff_error)
    signoff_passed = bool_field(signoff_report, "passed", "Passed", "success")
    if signoff_passed is not True:
        errors.append(f"Final figure/data sign-off report does not prove success: passed={signoff_passed!r}.")

    evidence_audit_report, evidence_audit_error = read_json(EVIDENCE_BUNDLE_AUDIT_REPORT)
    if evidence_audit_error:
        errors.append(evidence_audit_error)
    evidence_audit_passed = bool_field(evidence_audit_report, "passed", "Passed", "success")
    if evidence_audit_passed is not True:
        errors.append(f"Submission-ready evidence bundle audit does not prove success: passed={evidence_audit_passed!r}.")

    missing = [path for path in REQUIRED_EVIDENCE if not path.exists()]
    for path in missing:
        errors.append(f"Required final evidence artifact is missing: {path.relative_to(ROOT)}")

    if log_path:
        log_file = ROOT / log_path if not Path(log_path).is_absolute() else Path(log_path)
        if not log_file.exists():
            warnings.append(f"Combined terminal log was named but is not present: {log_path}")
        else:
            notes.append(f"Combined terminal log: {log_path}")
    else:
        warnings.append("SUBMISSION_READY_LOG was not provided.")

    passed = not errors
    return {
        "passed": passed,
        "core_gate_exit_code": core_exit,
        "figure_data_review_matrix_template_exit_code": review_matrix_template_exit,
        "figure_data_review_matrix_exit_code": review_matrix_exit,
        "figure_data_issue_register_exit_code": issue_register_exit,
        "figure_data_signoff_exit_code": signoff_exit,
        "submission_ready_script_audit_exit_code": script_audit_exit,
        "submission_ready_evidence_exit_code": evidence_exit,
        "submission_ready_evidence_audit_exit_code": evidence_audit_exit,
        "submission_ready_script_audit_passed": script_audit_passed,
        "core_report_passed": core_passed,
        "figure_data_review_matrix_template_passed": review_matrix_template_passed,
        "figure_data_review_matrix_passed": review_matrix_passed,
        "figure_data_issue_register_passed": issue_register_passed,
        "figure_data_signoff_passed": signoff_passed,
        "submission_ready_evidence_audit_passed": evidence_audit_passed,
        "combined_log": log_path,
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "required_evidence": [str(path.relative_to(ROOT)) for path in REQUIRED_EVIDENCE],
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Submission-Ready Gate Report",
        "",
        f"Passed: {result['passed']}",
        f"Core publication gate exit code: {result['core_gate_exit_code']}",
        f"Final figure/data review matrix template exit code: {result['figure_data_review_matrix_template_exit_code']}",
        f"Final figure/data review matrix exit code: {result['figure_data_review_matrix_exit_code']}",
        f"Final figure/data issue register exit code: {result['figure_data_issue_register_exit_code']}",
        f"Final figure/data sign-off exit code: {result['figure_data_signoff_exit_code']}",
        f"Submission-ready gate scripts audit exit code: {result['submission_ready_script_audit_exit_code']}",
        f"Submission-ready evidence bundle exit code: {result['submission_ready_evidence_exit_code']}",
        f"Submission-ready evidence bundle audit exit code: {result['submission_ready_evidence_audit_exit_code']}",
        f"Script audit passed: {result['submission_ready_script_audit_passed']}",
        f"Core report passed: {result['core_report_passed']}",
        f"Figure/data review matrix template passed: {result['figure_data_review_matrix_template_passed']}",
        f"Figure/data review matrix passed: {result['figure_data_review_matrix_passed']}",
        f"Figure/data issue register passed: {result['figure_data_issue_register_passed']}",
        f"Figure/data sign-off passed: {result['figure_data_signoff_passed']}",
        f"Evidence bundle audit passed: {result['submission_ready_evidence_audit_passed']}",
        f"Combined log: `{result['combined_log']}`",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.extend(["", "## Required Evidence"])
    lines.extend(f"- `{item}`" for item in result["required_evidence"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = build_report()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

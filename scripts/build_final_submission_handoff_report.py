"""Build the final submission handoff report."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
MANUSCRIPT_DIR = ROOT / "manuscript"

REPORT_MD = LOGS_DIR / "final_submission_handoff_report.md"
REPORT_JSON = LOGS_DIR / "final_submission_handoff_report.json"
LATEST_HANDOFF_LOG = LOGS_DIR / "final_submission_handoff_latest.log"

SUBMISSION_READY_REPORT = LOGS_DIR / "submission_ready_gate_report.json"
TERMINAL_RUN_RECORD = MANUSCRIPT_DIR / "submission_ready_terminal_run_record.json"
TERMINAL_RUN_RECORD_AUDIT = LOGS_DIR / "submission_ready_terminal_run_record_audit.json"
HANDOFF_EVIDENCE_AUDIT = LOGS_DIR / "final_submission_handoff_evidence_bundle_audit.json"
HANDOFF_EVIDENCE_MANIFEST = ROOT / "final_submission_handoff_evidence" / "evidence_manifest.json"
HANDOFF_EVIDENCE_MANIFEST_SHA256 = ROOT / "final_submission_handoff_evidence" / "evidence_manifest.sha256"


def read_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"Missing JSON report: {path.relative_to(ROOT)}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path.relative_to(ROOT)}: {exc}"
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

    gate_exit = int_env("FINAL_HANDOFF_GATE_EXIT_CODE")
    record_exit = int_env("FINAL_HANDOFF_RECORD_EXIT_CODE")
    record_audit_exit = int_env("FINAL_HANDOFF_RECORD_AUDIT_EXIT_CODE")
    evidence_exit = int_env("FINAL_HANDOFF_EVIDENCE_EXIT_CODE")
    evidence_audit_exit = int_env("FINAL_HANDOFF_EVIDENCE_AUDIT_EXIT_CODE")
    log_path = os.environ.get("FINAL_HANDOFF_LOG", "").strip()

    if gate_exit is None:
        errors.append("FINAL_HANDOFF_GATE_EXIT_CODE was not provided.")
    elif gate_exit != 0:
        errors.append(f"Submission-ready gate exit code is {gate_exit}.")

    if record_exit is None:
        errors.append("FINAL_HANDOFF_RECORD_EXIT_CODE was not provided.")
    elif record_exit != 0:
        errors.append(f"Terminal-run record exit code is {record_exit}.")

    if record_audit_exit is None:
        errors.append("FINAL_HANDOFF_RECORD_AUDIT_EXIT_CODE was not provided.")
    elif record_audit_exit != 0:
        errors.append(f"Terminal-run record audit exit code is {record_audit_exit}.")

    if evidence_exit is None:
        errors.append("FINAL_HANDOFF_EVIDENCE_EXIT_CODE was not provided.")
    elif evidence_exit != 0:
        errors.append(f"Final handoff evidence bundle exit code is {evidence_exit}.")

    if evidence_audit_exit is None:
        errors.append("FINAL_HANDOFF_EVIDENCE_AUDIT_EXIT_CODE was not provided.")
    elif evidence_audit_exit != 0:
        errors.append(f"Final handoff evidence bundle audit exit code is {evidence_audit_exit}.")

    submission_report, submission_error = read_json(SUBMISSION_READY_REPORT)
    if submission_error:
        errors.append(submission_error)
    submission_passed = bool_field(submission_report, "passed", "Passed", "success")
    if submission_passed is not True:
        errors.append(f"Submission-ready gate report does not prove success: passed={submission_passed!r}.")

    record, record_error = read_json(TERMINAL_RUN_RECORD)
    if record_error:
        errors.append(record_error)
    elif record.get("status") != "ready_for_submission":
        errors.append(f"Terminal-run record status is not ready_for_submission: {record.get('status')!r}.")

    record_audit, record_audit_error = read_json(TERMINAL_RUN_RECORD_AUDIT)
    if record_audit_error:
        errors.append(record_audit_error)
    record_audit_passed = bool_field(record_audit, "passed", "Passed", "success")
    if record_audit_passed is not True:
        errors.append(f"Terminal-run record audit does not prove success: passed={record_audit_passed!r}.")

    evidence_audit, evidence_audit_error = read_json(HANDOFF_EVIDENCE_AUDIT)
    if evidence_audit_error:
        errors.append(evidence_audit_error)
    evidence_audit_passed = bool_field(evidence_audit, "passed", "Passed", "success")
    if evidence_audit_passed is not True:
        errors.append(f"Final handoff evidence bundle audit does not prove success: passed={evidence_audit_passed!r}.")

    if not HANDOFF_EVIDENCE_MANIFEST.exists():
        errors.append(f"Final handoff evidence manifest is missing: {HANDOFF_EVIDENCE_MANIFEST.relative_to(ROOT)}")
    if not HANDOFF_EVIDENCE_MANIFEST_SHA256.exists():
        errors.append(
            f"Final handoff evidence manifest SHA256 sidecar is missing: "
            f"{HANDOFF_EVIDENCE_MANIFEST_SHA256.relative_to(ROOT)}"
        )

    if log_path:
        log_file = ROOT / log_path if not Path(log_path).is_absolute() else Path(log_path)
        if log_file.exists():
            notes.append(f"Final handoff log: {log_path}")
        else:
            warnings.append(f"Final handoff log was named but is not present: {log_path}")
    else:
        warnings.append("FINAL_HANDOFF_LOG was not provided.")

    return {
        "passed": not errors,
        "submission_ready_gate_exit_code": gate_exit,
        "terminal_run_record_exit_code": record_exit,
        "terminal_run_record_audit_exit_code": record_audit_exit,
        "final_handoff_evidence_exit_code": evidence_exit,
        "final_handoff_evidence_audit_exit_code": evidence_audit_exit,
        "submission_ready_report_passed": submission_passed,
        "terminal_run_record_audit_passed": record_audit_passed,
        "final_handoff_evidence_audit_passed": evidence_audit_passed,
        "final_handoff_evidence_manifest": str(HANDOFF_EVIDENCE_MANIFEST.relative_to(ROOT)),
        "final_handoff_evidence_manifest_sha256": str(HANDOFF_EVIDENCE_MANIFEST_SHA256.relative_to(ROOT)),
        "final_handoff_log": log_path,
        "final_handoff_latest_log": str(LATEST_HANDOFF_LOG.relative_to(ROOT)),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Final Submission Handoff Report",
        "",
        f"Passed: {result['passed']}",
        f"Submission-ready gate exit code: {result['submission_ready_gate_exit_code']}",
        f"Terminal-run record exit code: {result['terminal_run_record_exit_code']}",
        f"Terminal-run record audit exit code: {result['terminal_run_record_audit_exit_code']}",
        f"Final handoff evidence bundle exit code: {result['final_handoff_evidence_exit_code']}",
        f"Final handoff evidence bundle audit exit code: {result['final_handoff_evidence_audit_exit_code']}",
        f"Submission-ready report passed: {result['submission_ready_report_passed']}",
        f"Terminal-run record audit passed: {result['terminal_run_record_audit_passed']}",
        f"Final handoff evidence bundle audit passed: {result['final_handoff_evidence_audit_passed']}",
        f"Final handoff evidence manifest: `{result['final_handoff_evidence_manifest']}`",
        f"Final handoff evidence manifest SHA256: `{result['final_handoff_evidence_manifest_sha256']}`",
        f"Final handoff log: `{result['final_handoff_log']}`",
        f"Final handoff latest log: `{result['final_handoff_latest_log']}`",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = build_report()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

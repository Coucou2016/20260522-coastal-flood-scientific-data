"""Audit the external terminal run record for the submission-ready gate."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

RECORD_PATH = MANUSCRIPT_DIR / "submission_ready_terminal_run_record.json"
REPORT_MD = LOGS_DIR / "submission_ready_terminal_run_record_audit.md"
REPORT_JSON = LOGS_DIR / "submission_ready_terminal_run_record_audit.json"

APPROVED_STATUS = "ready_for_submission"
EXPECTED_COMMAND = "scripts\\run_submission_ready_gate.cmd"


def valid_iso_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def read_record(errors: list[str]) -> dict:
    if not RECORD_PATH.exists():
        errors.append(f"Missing terminal run record: {RECORD_PATH.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid terminal run record JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("Terminal run record must contain a JSON object.")
        return {}
    return value


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    record = read_record(errors)

    if record:
        if record.get("status") != APPROVED_STATUS:
            errors.append(
                f"Terminal run record status must be '{APPROVED_STATUS}' after a successful external run; "
                f"found {record.get('status')!r}."
            )

        runner = str(record.get("runner", "")).strip()
        if not runner:
            errors.append("Terminal run record runner is blank.")

        run_date = str(record.get("run_date", "")).strip()
        if not valid_iso_date(run_date):
            errors.append("Terminal run record run_date must be an ISO date such as 2026-06-03.")

        command = str(record.get("command", "")).strip()
        if command.lower() != EXPECTED_COMMAND.lower():
            errors.append(f"Terminal run command must be {EXPECTED_COMMAND!r}; found {command!r}.")

        exit_code = record.get("exit_code")
        if exit_code != 0:
            errors.append(f"Terminal run exit_code must be 0; found {exit_code!r}.")

        if record.get("submission_ready_report_passed") is not True:
            errors.append("submission_ready_report_passed must be true.")

        outputs = record.get("checked_outputs")
        if not isinstance(outputs, dict):
            errors.append("checked_outputs must be a JSON object.")
            outputs = {}

        for output, checked in outputs.items():
            if checked is not True:
                errors.append(f"Required output was not checked: {output}")
            path = ROOT / str(output)
            if not path.exists():
                warnings.append(f"Checked output is not currently present in this worktree: {output}")

        follow_up = record.get("blocking_follow_up")
        if not isinstance(follow_up, list):
            errors.append("blocking_follow_up must be a list.")
        elif follow_up:
            errors.append(f"blocking_follow_up must be empty before submission: {follow_up}")

        notes_text = str(record.get("notes", "")).strip()
        if notes_text:
            notes.append(notes_text)

    return {
        "passed": not errors,
        "record": str(RECORD_PATH.relative_to(ROOT)),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Submission-Ready Terminal Run Record Audit",
        "",
        f"Passed: {result['passed']}",
        f"Record: `{result['record']}`",
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
    result = audit()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

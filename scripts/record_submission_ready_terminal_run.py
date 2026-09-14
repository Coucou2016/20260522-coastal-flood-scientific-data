"""Record a successful external submission-ready gate run.

Run this after `scripts\run_submission_ready_gate.cmd` has completed in a
normal Windows terminal. The script verifies the final gate report, failure
summary, and key output artifacts before writing
`manuscript/submission_ready_terminal_run_record.json`.
"""

from __future__ import annotations

import getpass
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

RECORD_PATH = MANUSCRIPT_DIR / "submission_ready_terminal_run_record.json"
GATE_REPORT = LOGS_DIR / "submission_ready_gate_report.json"
FAILURE_SUMMARY = LOGS_DIR / "submission_ready_failure_summary.json"

CHECKED_OUTPUTS = [
    "logs\\submission_ready_gate_latest.log",
    "logs\\submission_ready_gate_report.md",
    "logs\\submission_ready_gate_report.json",
    "logs\\submission_ready_failure_summary.md",
    "submission_ready_gate_evidence\\evidence_manifest.json",
    "submission_ready_gate_evidence\\evidence_manifest.sha256",
    "publication_package.zip",
    "final_archive_manifest.json",
]


def read_json(path: Path, errors: list[str]) -> dict:
    if not path.exists():
        errors.append(f"Missing required JSON: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"JSON must contain an object: {path.relative_to(ROOT)}")
        return {}
    return value


def bool_field(value: dict, *names: str) -> bool | None:
    for name in names:
        candidate = value.get(name)
        if isinstance(candidate, bool):
            return candidate
        if isinstance(candidate, str) and candidate.lower() in {"true", "false"}:
            return candidate.lower() == "true"
    return None


def main() -> int:
    errors: list[str] = []

    gate_report = read_json(GATE_REPORT, errors)
    failure_summary = read_json(FAILURE_SUMMARY, errors)

    gate_passed = bool_field(gate_report, "passed", "Passed", "success")
    if gate_passed is not True:
        errors.append(f"Submission-ready gate report does not prove passed=True: {gate_passed!r}")

    summary_passed = bool_field(failure_summary, "passed", "Passed", "success")
    blocker_count = failure_summary.get("blocker_count")
    if summary_passed is not True:
        errors.append(f"Failure summary does not prove passed=True: {summary_passed!r}")
    if blocker_count not in (0, None):
        errors.append(f"Failure summary blocker_count must be 0; found {blocker_count!r}")

    checked_outputs: dict[str, bool] = {}
    for rel in CHECKED_OUTPUTS:
        exists = (ROOT / rel).exists()
        checked_outputs[rel] = exists
        if not exists:
            errors.append(f"Missing checked output: {rel}")

    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    record = {
        "status": "ready_for_submission",
        "runner": getpass.getuser(),
        "run_date": date.today().isoformat(),
        "command": "scripts\\run_submission_ready_gate.cmd",
        "working_directory": str(ROOT),
        "exit_code": 0,
        "submission_ready_report_passed": True,
        "checked_outputs": checked_outputs,
        "notes": "Recorded automatically after successful submission-ready gate outputs were present.",
        "blocking_follow_up": [],
    }

    MANUSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_PATH.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {RECORD_PATH.relative_to(ROOT)}")
    print("Passed: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit scripts that make up the final submission-ready gate."""

from __future__ import annotations

import json
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"

REPORT_MD = LOGS_DIR / "submission_ready_gate_scripts_audit.md"
REPORT_JSON = LOGS_DIR / "submission_ready_gate_scripts_audit.json"

PYTHON_SCRIPTS = [
    "scripts/audit_final_figure_data_issue_register.py",
    "scripts/audit_final_figure_data_review_matrix.py",
    "scripts/build_final_figure_data_review_matrix_template.py",
    "scripts/build_submission_ready_failure_summary.py",
    "scripts/record_submission_ready_terminal_run.py",
    "scripts/build_final_submission_handoff_evidence_bundle.py",
    "scripts/audit_final_submission_handoff_evidence_bundle.py",
    "scripts/build_final_submission_handoff_report.py",
    "scripts/audit_submission_ready_terminal_run_record.py",
    "scripts/audit_final_figure_data_signoff.py",
    "scripts/build_submission_ready_evidence_bundle.py",
    "scripts/audit_submission_ready_evidence_bundle.py",
    "scripts/build_submission_ready_report.py",
]

CMD_SCRIPTS = [
    "scripts/run_final_figure_data_issue_register_audit.cmd",
    "scripts/run_final_figure_data_review_matrix_audit.cmd",
    "scripts/build_final_figure_data_review_matrix_template.cmd",
    "scripts/build_submission_ready_failure_summary.cmd",
    "scripts/record_submission_ready_terminal_run.cmd",
    "scripts/build_final_submission_handoff_evidence_bundle.cmd",
    "scripts/run_final_submission_handoff_evidence_bundle_audit.cmd",
    "scripts/build_final_submission_handoff_report.cmd",
    "scripts/run_submission_ready_terminal_run_record_audit.cmd",
    "scripts/run_final_figure_data_signoff_audit.cmd",
    "scripts/run_submission_ready_gate_scripts_audit.cmd",
    "scripts/build_submission_ready_evidence_bundle.cmd",
    "scripts/run_submission_ready_evidence_bundle_audit.cmd",
    "scripts/run_submission_ready_gate.cmd",
    "scripts/run_final_submission_handoff.cmd",
    "scripts/run_publication_gate_logged.cmd",
    "scripts/run_all_publication_checks.cmd",
]

CONTENT_EXPECTATIONS = {
    "scripts/run_submission_ready_gate.cmd": [
        "scripts\\run_publication_gate.cmd",
        "scripts\\build_final_figure_data_review_matrix_template.cmd",
        "scripts\\run_final_figure_data_review_matrix_audit.cmd",
        "scripts\\run_final_figure_data_issue_register_audit.cmd",
        "scripts\\run_final_figure_data_signoff_audit.cmd",
        "scripts\\build_submission_ready_evidence_bundle.cmd",
        "scripts\\run_submission_ready_evidence_bundle_audit.cmd",
        "scripts\\build_submission_ready_report.py",
        "scripts\\build_submission_ready_failure_summary.cmd",
    ],
    "scripts/run_final_submission_handoff.cmd": [
        "EnableDelayedExpansion",
        "!ERRORLEVEL!",
        "scripts\\run_submission_ready_gate.cmd",
        "scripts\\record_submission_ready_terminal_run.cmd",
        "scripts\\run_submission_ready_terminal_run_record_audit.cmd",
        "scripts\\build_final_submission_handoff_evidence_bundle.cmd",
        "scripts\\run_final_submission_handoff_evidence_bundle_audit.cmd",
        "scripts\\build_final_submission_handoff_report.cmd",
    ],
    "scripts/run_final_figure_data_issue_register_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_final_figure_data_issue_register.py",
    ],
    "scripts/run_final_figure_data_review_matrix_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_final_figure_data_review_matrix.py",
    ],
    "scripts/build_final_figure_data_review_matrix_template.cmd": [
        "scripts\\run_python_checked.cmd scripts\\build_final_figure_data_review_matrix_template.py",
    ],
    "scripts/build_submission_ready_failure_summary.cmd": [
        "scripts\\run_python_checked.cmd scripts\\build_submission_ready_failure_summary.py",
    ],
    "scripts/record_submission_ready_terminal_run.cmd": [
        "scripts\\run_python_checked.cmd scripts\\record_submission_ready_terminal_run.py",
    ],
    "scripts/build_final_submission_handoff_evidence_bundle.cmd": [
        "scripts\\run_python_checked.cmd scripts\\build_final_submission_handoff_evidence_bundle.py",
    ],
    "scripts/run_final_submission_handoff_evidence_bundle_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_final_submission_handoff_evidence_bundle.py",
    ],
    "scripts/build_final_submission_handoff_report.cmd": [
        "scripts\\run_python_checked.cmd scripts\\build_final_submission_handoff_report.py",
    ],
    "scripts/run_submission_ready_terminal_run_record_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_submission_ready_terminal_run_record.py",
    ],
    "scripts/run_final_figure_data_signoff_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_final_figure_data_signoff.py",
    ],
    "scripts/run_submission_ready_gate_scripts_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_submission_ready_gate_scripts.py",
    ],
    "scripts/build_submission_ready_evidence_bundle.cmd": [
        "scripts\\run_python_checked.cmd scripts\\build_submission_ready_evidence_bundle.py",
    ],
    "scripts/run_submission_ready_evidence_bundle_audit.cmd": [
        "scripts\\run_python_checked.cmd scripts\\audit_submission_ready_evidence_bundle.py",
    ],
    "scripts/run_publication_gate_logged.cmd": [
        "scripts\\run_final_submission_handoff.cmd",
    ],
    "scripts/run_all_publication_checks.cmd": [
        "scripts\\run_final_submission_handoff.cmd",
    ],
}


def normalized(text: str) -> str:
    return " ".join(text.replace("/", "\\").lower().split())


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    for rel in PYTHON_SCRIPTS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"Missing Python script: {rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"Python compile failed for {rel}: {exc.msg}")

    for rel in CMD_SCRIPTS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"Missing command script: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        propagates_errorlevel = "exit /b %ERRORLEVEL%" in text
        propagates_status = "exit /b %STATUS%" in text
        if not propagates_errorlevel and not propagates_status and rel != "scripts/run_submission_ready_gate.cmd":
            warnings.append(f"Command script should propagate ERRORLEVEL explicitly: {rel}")
        if ">> \"%LOG%\" 2>&1" in text and "(" in text and ")" in text:
            if "enabledelayedexpansion" not in text.lower():
                warnings.append(f"Command script captures block-scoped status without delayed expansion: {rel}")

    for rel, expected_items in CONTENT_EXPECTATIONS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = normalized(path.read_text(encoding="utf-8", errors="replace"))
        for expected in expected_items:
            if normalized(expected) not in text:
                errors.append(f"{rel} does not reference expected command: {expected}")

    if not errors:
        notes.append("Submission-ready gate entrypoints and helper scripts are present and wired together.")

    return {
        "passed": not errors,
        "python_scripts": PYTHON_SCRIPTS,
        "cmd_scripts": CMD_SCRIPTS,
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Submission-Ready Gate Scripts Audit",
        "",
        f"Passed: {result['passed']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.extend(["", "## Python Scripts"])
    lines.extend(f"- `{item}`" for item in result["python_scripts"])
    lines.extend(["", "## Command Scripts"])
    lines.extend(f"- `{item}`" for item in result["cmd_scripts"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = audit()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

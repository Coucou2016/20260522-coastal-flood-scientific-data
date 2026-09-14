"""Build a concise failure/next-action summary for the final gate."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"

REPORT_MD = LOGS_DIR / "submission_ready_failure_summary.md"
REPORT_JSON = LOGS_DIR / "submission_ready_failure_summary.json"

REPORTS = [
    ("Submission-ready scripts", LOGS_DIR / "submission_ready_gate_scripts_audit.json"),
    ("Core publication gate", LOGS_DIR / "publication_gate_report.json"),
    ("Review matrix template", LOGS_DIR / "final_figure_data_review_matrix_template.json"),
    ("Review matrix audit", LOGS_DIR / "final_figure_data_review_matrix_audit.json"),
    ("Issue register audit", LOGS_DIR / "final_figure_data_issue_register_audit.json"),
    ("Figure/data sign-off audit", LOGS_DIR / "final_figure_data_signoff_audit.json"),
    ("Evidence bundle audit", LOGS_DIR / "submission_ready_evidence_bundle_audit.json"),
    ("Submission-ready gate", LOGS_DIR / "submission_ready_gate_report.json"),
]


def read_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"Missing report: {path.relative_to(ROOT)}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path.relative_to(ROOT)}: {exc}"
    if not isinstance(value, dict):
        return None, f"Report is not a JSON object: {path.relative_to(ROOT)}"
    return value, None


def report_passed(value: dict) -> bool | None:
    for key in ("passed", "Passed", "gate_passed", "success"):
        candidate = value.get(key)
        if isinstance(candidate, bool):
            return candidate
        if isinstance(candidate, str) and candidate.lower() in {"true", "false"}:
            return candidate.lower() == "true"
    return None


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def build_summary() -> dict:
    sections: list[dict] = []
    blockers: list[str] = []
    warnings: list[str] = []

    for label, path in REPORTS:
        value, error = read_json(path)
        if error:
            item = {
                "label": label,
                "report": str(path.relative_to(ROOT)),
                "passed": False,
                "errors": [error],
                "warnings": [],
                "notes": [],
            }
            sections.append(item)
            blockers.append(f"{label}: {error}")
            continue

        assert value is not None
        errors = as_list(value.get("errors"))
        report_warnings = as_list(value.get("warnings"))
        notes = as_list(value.get("notes"))
        passed = report_passed(value)

        if passed is not True and not errors:
            errors.append(f"Report does not prove passed=True; found {passed!r}.")

        for error_item in errors:
            blockers.append(f"{label}: {error_item}")
        for warning_item in report_warnings:
            warnings.append(f"{label}: {warning_item}")

        sections.append(
            {
                "label": label,
                "report": str(path.relative_to(ROOT)),
                "passed": passed,
                "errors": errors,
                "warnings": report_warnings,
                "notes": notes,
            }
        )

    return {
        "passed": not blockers,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "sections": sections,
    }


def write_reports(summary: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Submission-Ready Failure Summary",
        "",
        f"Passed: {summary['passed']}",
        f"Blockers: {summary['blocker_count']}",
        f"Warnings: {summary['warning_count']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in summary["blockers"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in summary["warnings"] or ["None"])
    lines.extend(["", "## Report Sections"])
    for section in summary["sections"]:
        lines.extend(
            [
                "",
                f"### {section['label']}",
                f"- Report: `{section['report']}`",
                f"- Passed: {section['passed']}",
            ]
        )
        if section["errors"]:
            lines.append("- Errors:")
            lines.extend(f"  - {item}" for item in section["errors"])
        if section["warnings"]:
            lines.append("- Warnings:")
            lines.extend(f"  - {item}" for item in section["warnings"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    summary = build_summary()
    write_reports(summary)
    print(f"Passed: {summary['passed']}")
    print(f"Blockers: {summary['blocker_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

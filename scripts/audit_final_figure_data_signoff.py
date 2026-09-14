"""Audit the final human sign-off for manuscript figures and figure data.

This check does not replace automated figure/source-data audits. It requires a
final reviewer to explicitly confirm that the rendered manuscript, embedded
images, source-data tables, generated rasters, and publication package were
checked together before submission.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

SIGNOFF_PATH = MANUSCRIPT_DIR / "final_figure_data_signoff.json"
REPORT_MD = LOGS_DIR / "final_figure_data_signoff_audit.md"
REPORT_JSON = LOGS_DIR / "final_figure_data_signoff_audit.json"

APPROVED_STATUS = "approved_for_submission"
PASS_STATUSES = {"pass", "not_applicable"}

REQUIRED_SCOPE = [
    "manuscript_markdown_reviewed",
    "review_html_reviewed",
    "all_manuscript_figures_reviewed",
    "all_embedded_images_reviewed",
    "all_source_data_tables_reviewed",
    "all_generated_rasters_reviewed",
    "publication_package_reviewed",
]

REQUIRED_CHECKS = [
    "figure_presence_and_order",
    "visual_rendering_quality",
    "source_data_traceability",
    "numeric_sanity",
    "terrain_connectivity_interpretation",
    "lowland_elevation_summary",
    "review_matrix_completed",
    "issue_register_closed",
    "residual_artifacts_disclosed",
]

EVIDENCE_FILES = [
    LOGS_DIR / "manuscript_figure_inventory.json",
    LOGS_DIR / "figure_deliverables_audit.json",
    LOGS_DIR / "figure_visual_quality_audit.json",
    LOGS_DIR / "figure_data_integrity_audit.json",
    LOGS_DIR / "manual_figure_review_sheet.md",
    LOGS_DIR / "publication_gate_report.json",
]


def load_json(path: Path) -> tuple[dict, list[str]]:
    if not path.exists():
        return {}, [f"Missing sign-off file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Invalid JSON in {path}: {exc}"]
    if not isinstance(value, dict):
        return {}, [f"Sign-off file must contain a JSON object: {path}"]
    return value, []


def valid_iso_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    signoff, load_errors = load_json(SIGNOFF_PATH)
    errors.extend(load_errors)

    if not errors:
        if signoff.get("status") != APPROVED_STATUS:
            errors.append(
                f"Sign-off status must be '{APPROVED_STATUS}' after final review; "
                f"found {signoff.get('status')!r}."
            )

        reviewer = str(signoff.get("reviewer", "")).strip()
        if not reviewer:
            errors.append("Sign-off reviewer is blank.")

        review_date = str(signoff.get("review_date", "")).strip()
        if not valid_iso_date(review_date):
            errors.append("Sign-off review_date must be an ISO date such as 2026-06-02.")

        scope = signoff.get("scope")
        if not isinstance(scope, dict):
            errors.append("Sign-off scope must be a JSON object.")
            scope = {}
        for key in REQUIRED_SCOPE:
            if scope.get(key) is not True:
                errors.append(f"Required scope flag is not true: {key}")

        checks = signoff.get("checks")
        if not isinstance(checks, list):
            errors.append("Sign-off checks must be a list.")
            checks = []

        check_map = {}
        for index, item in enumerate(checks, start=1):
            if not isinstance(item, dict):
                errors.append(f"Check entry {index} must be a JSON object.")
                continue
            check_id = str(item.get("id", "")).strip()
            if not check_id:
                errors.append(f"Check entry {index} is missing an id.")
                continue
            if check_id in check_map:
                errors.append(f"Duplicate sign-off check id: {check_id}")
            check_map[check_id] = item

        for check_id in REQUIRED_CHECKS:
            item = check_map.get(check_id)
            if item is None:
                errors.append(f"Missing required sign-off check: {check_id}")
                continue
            status = str(item.get("status", "")).strip()
            if status not in PASS_STATUSES:
                errors.append(f"Check {check_id} must be one of {sorted(PASS_STATUSES)}; found {status!r}.")
            evidence = str(item.get("evidence", "")).strip()
            if not evidence:
                errors.append(f"Check {check_id} must include evidence.")

        blocking_issues = signoff.get("blocking_issues")
        if not isinstance(blocking_issues, list):
            errors.append("blocking_issues must be a list.")
        elif blocking_issues:
            errors.append("blocking_issues must be empty before submission.")

        accepted_limitations = signoff.get("accepted_limitations", [])
        if not isinstance(accepted_limitations, list):
            errors.append("accepted_limitations must be a list.")
        elif accepted_limitations:
            notes.append(f"Accepted limitations listed: {len(accepted_limitations)}")

    missing_evidence = [path for path in EVIDENCE_FILES if not path.exists()]
    for path in missing_evidence:
        warnings.append(f"Evidence file not present yet: {path.relative_to(ROOT)}")

    passed = not errors
    return {
        "passed": passed,
        "signoff_file": str(SIGNOFF_PATH.relative_to(ROOT)),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "required_scope": REQUIRED_SCOPE,
        "required_checks": REQUIRED_CHECKS,
        "evidence_files": [str(path.relative_to(ROOT)) for path in EVIDENCE_FILES],
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Final Figure/Data Sign-off Audit",
        "",
        f"Passed: {result['passed']}",
        f"Sign-off file: `{result['signoff_file']}`",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.extend(["", "## Required Checks"])
    lines.extend(f"- {item}" for item in result["required_checks"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = audit()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

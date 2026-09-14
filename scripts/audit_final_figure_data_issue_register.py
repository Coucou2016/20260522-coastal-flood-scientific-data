"""Audit the final figure/data issue register.

The issue register records visual defects, source-data mismatches, suspicious
numeric patterns, and accepted non-blocking limitations found during final
manuscript figure review. Submission is blocked until all issues are resolved,
accepted as non-blocking, or marked not applicable with evidence.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

REGISTER_PATH = MANUSCRIPT_DIR / "final_figure_data_issue_register.json"
REPORT_MD = LOGS_DIR / "final_figure_data_issue_register_audit.md"
REPORT_JSON = LOGS_DIR / "final_figure_data_issue_register_audit.json"

APPROVED_STATUS = "ready_for_submission"
ATTESTED_STATUS = "confirmed"
ALLOWED_ISSUE_STATUS = {"resolved", "accepted_non_blocking", "not_applicable"}
BLOCKING_SEVERITIES = {"critical", "major"}
ALLOWED_SEVERITIES = {"critical", "major", "minor", "note"}


def read_register(errors: list[str]) -> dict:
    if not REGISTER_PATH.exists():
        errors.append(f"Missing issue register: {REGISTER_PATH.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid issue register JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("Issue register must contain a JSON object.")
        return {}
    return value


def valid_iso_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def audit_issue(index: int, issue: dict, errors: list[str], warnings: list[str]) -> None:
    prefix = f"Issue {index}"
    issue_id = str(issue.get("id", "")).strip()
    if not issue_id:
        errors.append(f"{prefix} is missing id.")
    else:
        prefix = f"Issue {issue_id}"

    target = str(issue.get("target", "")).strip()
    if not target:
        errors.append(f"{prefix} is missing target.")

    description = str(issue.get("description", "")).strip()
    if not description:
        errors.append(f"{prefix} is missing description.")

    severity = str(issue.get("severity", "")).strip()
    if severity not in ALLOWED_SEVERITIES:
        errors.append(f"{prefix} severity must be one of {sorted(ALLOWED_SEVERITIES)}; found {severity!r}.")

    status = str(issue.get("status", "")).strip()
    if status not in ALLOWED_ISSUE_STATUS:
        errors.append(f"{prefix} status must be one of {sorted(ALLOWED_ISSUE_STATUS)}; found {status!r}.")

    evidence = str(issue.get("evidence", "")).strip()
    if not evidence:
        errors.append(f"{prefix} must include evidence.")

    resolution = str(issue.get("resolution", "")).strip()
    if not resolution:
        errors.append(f"{prefix} must include resolution.")

    if severity in BLOCKING_SEVERITIES and status != "resolved":
        errors.append(f"{prefix} has blocking severity {severity!r} and must be resolved, not {status!r}.")

    if status == "accepted_non_blocking":
        rationale = str(issue.get("acceptance_rationale", "")).strip()
        if not rationale:
            errors.append(f"{prefix} accepted_non_blocking issues require acceptance_rationale.")
        if severity in BLOCKING_SEVERITIES:
            errors.append(f"{prefix} cannot accept {severity!r} issue as non-blocking.")

    if status == "not_applicable" and severity != "note":
        warnings.append(f"{prefix} is not_applicable but severity is {severity!r}; check whether severity should be 'note'.")


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    register = read_register(errors)

    if register:
        if register.get("status") != APPROVED_STATUS:
            errors.append(
                f"Issue register status must be '{APPROVED_STATUS}' after final review; "
                f"found {register.get('status')!r}."
            )

        reviewer = str(register.get("reviewer", "")).strip()
        if not reviewer:
            errors.append("Issue register reviewer is blank.")

        last_updated = str(register.get("last_updated", "")).strip()
        if not valid_iso_date(last_updated):
            errors.append("Issue register last_updated must be an ISO date such as 2026-06-03.")

        attestation = register.get("no_unresolved_issues_attestation")
        if not isinstance(attestation, dict):
            errors.append("no_unresolved_issues_attestation must be a JSON object.")
        else:
            if attestation.get("status") != ATTESTED_STATUS:
                errors.append(
                    f"no_unresolved_issues_attestation.status must be '{ATTESTED_STATUS}'; "
                    f"found {attestation.get('status')!r}."
                )
            if not str(attestation.get("evidence", "")).strip():
                errors.append("no_unresolved_issues_attestation must include evidence.")

        issues = register.get("issues")
        if not isinstance(issues, list):
            errors.append("issues must be a list.")
            issues = []

        seen_ids: set[str] = set()
        for index, issue in enumerate(issues, start=1):
            if not isinstance(issue, dict):
                errors.append(f"Issue {index} must be a JSON object.")
                continue
            issue_id = str(issue.get("id", "")).strip()
            if issue_id:
                if issue_id in seen_ids:
                    errors.append(f"Duplicate issue id: {issue_id}")
                seen_ids.add(issue_id)
            audit_issue(index, issue, errors, warnings)

        if not issues:
            notes.append("No figure/data issues are listed; attestation evidence must support this.")
        else:
            notes.append(f"Reviewed issue entries: {len(issues)}")

    result = {
        "passed": not errors,
        "register": str(REGISTER_PATH.relative_to(ROOT)),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }
    return result


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Final Figure/Data Issue Register Audit",
        "",
        f"Passed: {result['passed']}",
        f"Register: `{result['register']}`",
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

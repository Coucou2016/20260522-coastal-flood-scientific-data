"""Audit the final per-figure/source-data review matrix."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

MATRIX_PATH = MANUSCRIPT_DIR / "final_figure_data_review_matrix.json"
TEMPLATE_PATH = MANUSCRIPT_DIR / "final_figure_data_review_matrix_template.json"
REPORT_MD = LOGS_DIR / "final_figure_data_review_matrix_audit.md"
REPORT_JSON = LOGS_DIR / "final_figure_data_review_matrix_audit.json"

APPROVED_STATUS = "ready_for_submission"
ATTESTED_STATUS = "confirmed"
PASS_STATUSES = {"pass", "accepted_non_blocking", "not_applicable"}
ALLOWED_ARTIFACT_TYPES = {"figure", "embedded_image", "source_data_table", "generated_raster", "package_artifact"}

REQUIRED_ROW_FLAGS = [
    "caption_matches_rendered_artifact",
    "rendered_artifact_checked",
    "source_data_checked",
    "numeric_sanity_checked",
    "visual_quality_checked",
    "package_artifact_checked",
    "issue_register_cross_checked",
]


def valid_iso_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def read_matrix(errors: list[str]) -> dict:
    if not MATRIX_PATH.exists():
        errors.append(f"Missing review matrix: {MATRIX_PATH.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid review matrix JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("Review matrix must contain a JSON object.")
        return {}
    return value


def read_template_required_artifacts(errors: list[str]) -> set[tuple[str, str]]:
    if not TEMPLATE_PATH.exists():
        errors.append(f"Missing review matrix template: {TEMPLATE_PATH.relative_to(ROOT)}")
        return set()
    try:
        value = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid review matrix template JSON: {exc}")
        return set()
    if not isinstance(value, dict):
        errors.append("Review matrix template must contain a JSON object.")
        return set()

    artifacts = value.get("required_artifacts")
    if not isinstance(artifacts, list):
        errors.append("Review matrix template required_artifacts must be a list.")
        return set()
    if not artifacts:
        errors.append("Review matrix template did not identify any required artifacts.")
        return set()

    keys: set[tuple[str, str]] = set()
    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            errors.append(f"Template required artifact {index} must be a JSON object.")
            continue
        artifact_type = str(artifact.get("artifact_type", "")).strip()
        artifact_id = str(artifact.get("artifact_id", "")).strip()
        if artifact_type and artifact_id:
            keys.add((artifact_type, artifact_id))
    return keys


def audit_row(index: int, row: dict, errors: list[str], warnings: list[str]) -> None:
    label = str(row.get("artifact_id", "")).strip()
    prefix = f"Row {index}" if not label else f"Row {index} ({label})"

    if not label:
        errors.append(f"{prefix} is missing artifact_id.")

    artifact_type = str(row.get("artifact_type", "")).strip()
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        errors.append(
            f"{prefix} artifact_type must be one of figure, embedded_image, source_data_table, "
            f"generated_raster, package_artifact; found {artifact_type!r}."
        )

    status = str(row.get("status", "")).strip()
    if status not in PASS_STATUSES:
        errors.append(f"{prefix} status must be one of {sorted(PASS_STATUSES)}; found {status!r}.")

    evidence = str(row.get("evidence", "")).strip()
    if not evidence:
        errors.append(f"{prefix} must include evidence.")

    notes = str(row.get("notes", "")).strip()
    if status in {"accepted_non_blocking", "not_applicable"} and not notes:
        errors.append(f"{prefix} with status {status!r} must include notes explaining the decision.")

    for flag in REQUIRED_ROW_FLAGS:
        value = row.get(flag)
        if value is not True:
            errors.append(f"{prefix} required flag is not true: {flag}")

    if artifact_type in {"source_data_table", "generated_raster"}:
        if row.get("caption_matches_rendered_artifact") is True:
            warnings.append(f"{prefix} is data/raster artifact; confirm caption flag means linked caption/source traceability.")


def audit_required_artifact(index: int, artifact: dict, errors: list[str]) -> str:
    label = str(artifact.get("artifact_id", "")).strip()
    prefix = f"Required artifact {index}" if not label else f"Required artifact {label}"

    if not label:
        errors.append(f"{prefix} is missing artifact_id.")

    artifact_type = str(artifact.get("artifact_type", "")).strip()
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        errors.append(
            f"{prefix} artifact_type must be one of figure, embedded_image, source_data_table, "
            f"generated_raster, package_artifact; found {artifact_type!r}."
        )

    evidence = str(artifact.get("evidence", "")).strip()
    if not evidence:
        errors.append(f"{prefix} must include evidence for why this artifact is required.")

    return label


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    matrix = read_matrix(errors)
    template_required_keys = read_template_required_artifacts(errors)

    if matrix:
        if matrix.get("status") != APPROVED_STATUS:
            errors.append(
                f"Review matrix status must be '{APPROVED_STATUS}' after final review; "
                f"found {matrix.get('status')!r}."
            )

        reviewer = str(matrix.get("reviewer", "")).strip()
        if not reviewer:
            errors.append("Review matrix reviewer is blank.")

        review_date = str(matrix.get("review_date", "")).strip()
        if not valid_iso_date(review_date):
            errors.append("Review matrix review_date must be an ISO date such as 2026-06-03.")

        required_artifacts = matrix.get("required_artifacts")
        if not isinstance(required_artifacts, list):
            errors.append("Review matrix required_artifacts must be a list.")
            required_artifacts = []
        if not required_artifacts:
            errors.append("Review matrix required_artifacts must list every manuscript figure/source-data artifact.")

        required_keys: set[tuple[str, str]] = set()
        for index, artifact in enumerate(required_artifacts, start=1):
            if not isinstance(artifact, dict):
                errors.append(f"Required artifact {index} must be a JSON object.")
                continue
            artifact_id = audit_required_artifact(index, artifact, errors)
            artifact_type = str(artifact.get("artifact_type", "")).strip()
            if artifact_type and artifact_id:
                if (artifact_type, artifact_id) in required_keys:
                    errors.append(f"Duplicate required artifact key: {artifact_type}:{artifact_id}")
                required_keys.add((artifact_type, artifact_id))

        missing_template_keys = sorted(template_required_keys - required_keys)
        for artifact_type, artifact_id in missing_template_keys:
            errors.append(
                f"Template artifact is absent from final required_artifacts: "
                f"{artifact_type}:{artifact_id}"
            )

        rows = matrix.get("rows")
        if not isinstance(rows, list):
            errors.append("Review matrix rows must be a list.")
            rows = []
        if not rows:
            errors.append("Review matrix must include at least one completed artifact row.")

        seen_keys: set[tuple[str, str]] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"Row {index} must be a JSON object.")
                continue
            artifact_id = str(row.get("artifact_id", "")).strip()
            artifact_type = str(row.get("artifact_type", "")).strip()
            if artifact_id and artifact_type:
                if (artifact_type, artifact_id) in seen_keys:
                    errors.append(f"Duplicate review matrix artifact key: {artifact_type}:{artifact_id}")
                seen_keys.add((artifact_type, artifact_id))
            audit_row(index, row, errors, warnings)

        missing_rows = sorted(required_keys - seen_keys)
        for artifact_type, artifact_id in missing_rows:
            errors.append(f"Required artifact has no completed review row: {artifact_type}:{artifact_id}")

        extra_rows = sorted(seen_keys - required_keys)
        for artifact_type, artifact_id in extra_rows:
            warnings.append(f"Review row is not listed in required_artifacts: {artifact_type}:{artifact_id}")

        attestation = matrix.get("completion_attestation")
        if not isinstance(attestation, dict):
            errors.append("completion_attestation must be a JSON object.")
        else:
            if attestation.get("status") != ATTESTED_STATUS:
                errors.append(
                    f"completion_attestation.status must be '{ATTESTED_STATUS}'; "
                    f"found {attestation.get('status')!r}."
                )
            if not str(attestation.get("evidence", "")).strip():
                errors.append("completion_attestation must include evidence.")

        notes.append(f"Reviewed matrix rows: {len(rows)}")

    return {
        "passed": not errors,
        "matrix": str(MATRIX_PATH.relative_to(ROOT)),
        "template": str(TEMPLATE_PATH.relative_to(ROOT)),
        "required_row_flags": REQUIRED_ROW_FLAGS,
        "required_artifact_count": len(matrix.get("required_artifacts", [])) if matrix else 0,
        "template_required_artifact_count": len(template_required_keys),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Final Figure/Data Review Matrix Audit",
        "",
        f"Passed: {result['passed']}",
        f"Matrix: `{result['matrix']}`",
        f"Template: `{result['template']}`",
        f"Required artifact count: {result['required_artifact_count']}",
        f"Template required artifact count: {result['template_required_artifact_count']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.extend(["", "## Required Row Flags"])
    lines.extend(f"- `{item}`" for item in result["required_row_flags"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = audit()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

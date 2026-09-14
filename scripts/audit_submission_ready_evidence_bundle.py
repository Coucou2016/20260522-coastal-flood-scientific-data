"""Audit the submission-ready evidence bundle.

This is the final integrity check for the evidence package produced by
`build_submission_ready_evidence_bundle.py`. It verifies that the bundle
manifest exists, its checksum sidecar matches, and the key final-submission
artifacts are represented in the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
BUNDLE_DIR = ROOT / "submission_ready_gate_evidence"
MANIFEST = BUNDLE_DIR / "evidence_manifest.json"
MANIFEST_SHA256 = BUNDLE_DIR / "evidence_manifest.sha256"

REPORT_MD = LOGS_DIR / "submission_ready_evidence_bundle_audit.md"
REPORT_JSON = LOGS_DIR / "submission_ready_evidence_bundle_audit.json"

REQUIRED_SOURCES = {
    "PUBLICATION_GATE_TERMINAL_RUN.md",
    "publication_gate_evidence/evidence_manifest.json",
    "publication_gate_evidence/evidence_manifest.sha256",
    "manuscript/final_figure_data_signoff.json",
    "manuscript/final_figure_data_signoff.md",
    "manuscript/final_figure_data_issue_register.json",
    "manuscript/final_figure_data_issue_register.md",
    "manuscript/final_figure_data_review_matrix.json",
    "manuscript/final_figure_data_review_matrix.md",
    "manuscript/final_figure_data_review_matrix_template.json",
    "logs/submission_ready_gate_scripts_audit.md",
    "logs/submission_ready_gate_scripts_audit.json",
    "logs/publication_gate_report.md",
    "logs/publication_gate_report.json",
    "logs/final_figure_data_review_matrix_template.md",
    "logs/final_figure_data_review_matrix_template.json",
    "logs/final_figure_data_review_matrix_audit.md",
    "logs/final_figure_data_review_matrix_audit.json",
    "logs/final_figure_data_issue_register_audit.md",
    "logs/final_figure_data_issue_register_audit.json",
    "logs/final_figure_data_signoff_audit.md",
    "logs/final_figure_data_signoff_audit.json",
    "publication_package.zip",
    "final_archive_manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(errors: list[str]) -> dict:
    if not MANIFEST.exists():
        errors.append(f"Missing evidence manifest: {MANIFEST.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid evidence manifest JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("Evidence manifest must be a JSON object.")
        return {}
    return value


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    manifest = load_manifest(errors)

    if not MANIFEST_SHA256.exists():
        errors.append(f"Missing manifest SHA256 sidecar: {MANIFEST_SHA256.relative_to(ROOT)}")
    elif MANIFEST.exists():
        sidecar = MANIFEST_SHA256.read_text(encoding="utf-8").strip()
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+evidence_manifest\.json", sidecar)
        if not match:
            errors.append("Manifest SHA256 sidecar must be '<64 hex>  evidence_manifest.json'.")
        else:
            expected = match.group(1).lower()
            actual = sha256_file(MANIFEST)
            if expected != actual:
                errors.append("Manifest SHA256 sidecar does not match evidence_manifest.json.")

    entries = manifest.get("entries", []) if manifest else []
    if not isinstance(entries, list):
        errors.append("Evidence manifest entries must be a list.")
        entries = []

    sources: set[str] = set()
    bundle_files: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"Evidence entry {index} must be a JSON object.")
            continue
        source = str(entry.get("source", "")).replace("\\", "/")
        source_size = entry.get("source_bytes")
        source_digest = str(entry.get("source_sha256", ""))
        bundle_file = str(entry.get("bundle_file", ""))
        digest = str(entry.get("sha256", ""))
        size = entry.get("bytes")

        if not source:
            errors.append(f"Evidence entry {index} is missing source.")
        else:
            sources.add(source)
            source_path = ROOT / source
            if not source_path.exists():
                errors.append(f"Evidence source is missing from worktree: {source}")
            else:
                if not isinstance(source_size, int) or source_size != source_path.stat().st_size:
                    errors.append(f"Evidence source byte count mismatch for {source}.")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", source_digest):
                    errors.append(f"Evidence source SHA256 is invalid for {source}.")
                elif sha256_file(source_path) != source_digest.lower():
                    errors.append(f"Evidence source SHA256 mismatch for {source}.")
        if not bundle_file:
            errors.append(f"Evidence entry {index} is missing bundle_file.")
        elif bundle_file in bundle_files:
            errors.append(f"Duplicate bundle file in manifest: {bundle_file}")
        else:
            bundle_files.add(bundle_file)

        target = BUNDLE_DIR / bundle_file if bundle_file else None
        if target and not target.exists():
            errors.append(f"Manifest bundle file is missing: {bundle_file}")
        elif target:
            actual_size = target.stat().st_size
            if not isinstance(size, int) or size != actual_size:
                errors.append(f"Manifest byte count mismatch for {bundle_file}.")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                errors.append(f"Manifest SHA256 is invalid for {bundle_file}.")
            elif sha256_file(target) != digest.lower():
                errors.append(f"Manifest SHA256 mismatch for {bundle_file}.")

    missing_sources = sorted(REQUIRED_SOURCES - sources)
    for source in missing_sources:
        errors.append(f"Required source is absent from evidence bundle: {source}")

    allowed_bundle_files = bundle_files | {"evidence_manifest.json", "evidence_manifest.sha256"}
    if BUNDLE_DIR.exists():
        for item in BUNDLE_DIR.iterdir():
            if item.name not in allowed_bundle_files:
                errors.append(f"Unexpected file in submission-ready evidence bundle: {item.name}")

    manifest_passed = manifest.get("passed") if manifest else None
    if manifest_passed is not True:
        errors.append(f"Evidence manifest does not report passed=True: {manifest_passed!r}")

    missing_list = manifest.get("missing", []) if manifest else []
    if missing_list:
        errors.append(f"Evidence manifest lists missing files: {missing_list}")

    if not errors:
        notes.append("Submission-ready evidence bundle manifest and SHA256 sidecar are internally consistent.")

    return {
        "passed": not errors,
        "bundle": str(BUNDLE_DIR.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_sha256": str(MANIFEST_SHA256.relative_to(ROOT)),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "required_sources": sorted(REQUIRED_SOURCES),
        "entry_count": len(entries),
    }


def write_reports(result: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Submission-Ready Evidence Bundle Audit",
        "",
        f"Passed: {result['passed']}",
        f"Bundle: `{result['bundle']}`",
        f"Manifest: `{result['manifest']}`",
        f"Manifest SHA256: `{result['manifest_sha256']}`",
        f"Entry count: {result['entry_count']}",
        "",
        "## Errors",
    ]
    lines.extend(f"- {item}" for item in result["errors"] or ["None"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in result["warnings"] or ["None"])
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result["notes"] or ["None"])
    lines.extend(["", "## Required Sources"])
    lines.extend(f"- `{item}`" for item in result["required_sources"])
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = audit()
    write_reports(result)
    print(f"Passed: {result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

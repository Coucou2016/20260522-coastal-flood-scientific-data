from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "submission_artifact_consistency_audit.txt"
REPORT_JSON = LOG_DIR / "submission_artifact_consistency_audit.json"

MAIN_MANUSCRIPT = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md"
REVIEW_HTML = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript_review.html"
PACKAGE_DIR = ROOT / "publication_package"
PACKAGE_ZIP = ROOT / "publication_package.zip"
COMPLETION_STATUS = ROOT / "completion_status.json"
FAILED_STATUS = ROOT / "publication_package_failed_status.json"
FINAL_ARCHIVE_MANIFEST = ROOT / "final_archive_manifest.json"
ROOT_PACKAGE_MANIFEST = ROOT / "package_manifest.json"
PACKAGED_PACKAGE_MANIFEST = PACKAGE_DIR / "package_manifest.json"


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path, audit: Audit) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        audit.error(f"Missing required artifact: {rel(path)}")
    except OSError as exc:
        audit.error(f"Cannot read {rel(path)}: {exc}")
    return ""


def load_json(path: Path, audit: Audit, required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            audit.error(f"Missing required JSON artifact: {rel(path)}")
    except json.JSONDecodeError as exc:
        audit.error(f"Invalid JSON in {rel(path)}: {exc}")
    except OSError as exc:
        audit.error(f"Cannot read {rel(path)}: {exc}")
    return None


def first_present(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def archive_zip_info(manifest: dict[str, Any]) -> dict[str, Any] | None:
    for key in ["publication_package_zip", "publication_package.zip", "zip", "archive", "final_archive"]:
        value = manifest.get(key)
        if isinstance(value, dict):
            return value
    for value in manifest.values():
        if isinstance(value, dict) and any(key in value for key in ["sha256", "zip_sha256", "bytes", "size_bytes"]):
            return value
    return None


def package_manifest_entries(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, list):
        return [item for item in manifest if isinstance(item, dict)]
    if not isinstance(manifest, dict):
        return []
    for key in ["files", "entries", "manifest", "package_files"]:
        value = manifest.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def entry_path(entry: dict[str, Any]) -> str | None:
    value = first_present(entry, ["path", "file", "name", "relative_path"])
    return str(value).replace("\\", "/") if value else None


def entry_sha(entry: dict[str, Any]) -> str | None:
    value = first_present(entry, ["sha256", "hash", "digest"])
    return str(value).lower() if value else None


def entry_size(entry: dict[str, Any]) -> int | None:
    value = first_present(entry, ["bytes", "size", "size_bytes"])
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def figure_numbers(text: str) -> set[int]:
    return {int(value) for value in re.findall(r"\b(?:Figure|Fig\.?)\s+([0-9]+)\b", text, flags=re.IGNORECASE)}


def table_numbers(text: str) -> set[int]:
    return {int(value) for value in re.findall(r"\bTable\s+([0-9]+)\b", text, flags=re.IGNORECASE)}


def validation_text_has_failure(text: str) -> bool:
    failure_patterns = [
        r"(?m)^\s*(?:failed|error|errors|exception|traceback)\b",
        r"\btraceback \(most recent call last\)",
        r"\bvalidation failed\b",
        r"\bfailed with exit code\s+[1-9]\d*\b",
        r"\berrors?\s*:\s*[1-9]\d*\b",
        r"\bfailed\s*:\s*[1-9]\d*\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in failure_patterns)


def audit_text_html_consistency(audit: Audit) -> None:
    manuscript = read_text(MAIN_MANUSCRIPT, audit)
    html = read_text(REVIEW_HTML, audit)
    if not manuscript or not html:
        return

    md_figures = figure_numbers(manuscript)
    html_figures = figure_numbers(re.sub(r"<[^>]+>", " ", html))
    if md_figures and html_figures and md_figures != html_figures:
        audit.error(f"Markdown figure numbers {sorted(md_figures)} do not match review HTML figure numbers {sorted(html_figures)}.")

    md_tables = table_numbers(manuscript)
    html_tables = table_numbers(re.sub(r"<[^>]+>", " ", html))
    if md_tables and html_tables and md_tables != html_tables:
        audit.error(f"Markdown table numbers {sorted(md_tables)} do not match review HTML table numbers {sorted(html_tables)}.")

    try:
        if REVIEW_HTML.stat().st_mtime < MAIN_MANUSCRIPT.stat().st_mtime:
            audit.error("Review HTML is older than the main manuscript Markdown; rebuild the HTML before submission.")
    except OSError as exc:
        audit.error(f"Cannot compare manuscript/HTML timestamps: {exc}")


def audit_completion_status(audit: Audit) -> None:
    status = load_json(COMPLETION_STATUS, audit)
    if isinstance(status, dict) and status.get("status") != "finalized":
        audit.error("completion_status.json does not report finalized status.")
    if FAILED_STATUS.exists():
        audit.error("publication_package_failed_status.json exists; remove stale failure state by rerunning finalization successfully.")


def audit_audit_logs(audit: Audit) -> None:
    log_specs = [
        (LOG_DIR / "python_runtime_dependencies_audit.json", "Python runtime dependencies audit"),
        (LOG_DIR / "manuscript_figure_inventory.json", "manuscript figure inventory"),
        (LOG_DIR / "figure_deliverables_audit.json", "figure deliverables audit"),
        (LOG_DIR / "figure_visual_quality_audit.json", "figure visual-quality audit"),
        (LOG_DIR / "manual_figure_review_sheet.json", "manual figure review sheet"),
        (LOG_DIR / "figure_data_integrity_audit.json", "figure/source-data audit"),
        (LOG_DIR / "manuscript_submission_text_audit.json", "manuscript text audit"),
        (LOG_DIR / "reference_metadata_audit.json", "reference metadata audit"),
        (LOG_DIR / "journal_submission_metadata_audit.json", "journal submission metadata audit"),
        (LOG_DIR / "repository_deposit_readiness_audit.json", "repository deposit readiness audit"),
    ]
    for path, label in log_specs:
        data = load_json(path, audit)
        if not isinstance(data, dict):
            continue
        errors = data.get("errors")
        warnings = data.get("warnings")
        if errors:
            audit.error(f"{label} still reports errors in {rel(path)}.")
        if warnings:
            audit.error(f"{label} still reports warnings in strict final-gate mode: {rel(path)}.")
        if data.get("passed") is False:
            audit.error(f"{label} reports passed=false in {rel(path)}.")
        if path.name == "manuscript_figure_inventory.json":
            image_count = data.get("image_count")
            error_count = data.get("error_count")
            records = data.get("records")
            if not isinstance(image_count, int) or image_count <= 0:
                audit.error(f"Manuscript figure inventory does not record any images in {rel(path)}.")
            if error_count not in (0, None):
                audit.error(f"Manuscript figure inventory reports {error_count} image error(s) in {rel(path)}.")
            if not isinstance(records, list) or len(records) != image_count:
                audit.error(f"Manuscript figure inventory record count does not match image_count in {rel(path)}.")

    text_logs = [
        LOG_DIR / "publication_package_validation.txt",
        LOG_DIR / "final_archive_validation.txt",
    ]
    for path in text_logs:
        text = read_text(path, audit)
        if text and validation_text_has_failure(text):
            audit.error(f"Validation log contains failure wording: {rel(path)}")


def audit_archive_manifest(audit: Audit) -> None:
    if not PACKAGE_DIR.exists():
        audit.error("publication_package/ is missing.")
    if not PACKAGE_ZIP.exists():
        audit.error("publication_package.zip is missing.")
        return

    manifest = load_json(FINAL_ARCHIVE_MANIFEST, audit)
    if not isinstance(manifest, dict):
        return
    zip_info = archive_zip_info(manifest)
    if zip_info is None:
        audit.error("final_archive_manifest.json does not contain ZIP metadata.")
        return
    expected_size = first_present(zip_info, ["bytes", "size", "size_bytes", "zip_bytes", "archive_bytes"])
    expected_sha = first_present(zip_info, ["sha256", "zip_sha256", "archive_sha256", "publication_package_zip_sha256"])
    actual_size = PACKAGE_ZIP.stat().st_size
    actual_sha = sha256_file(PACKAGE_ZIP)
    if expected_size is None:
        audit.error("final_archive_manifest.json does not record publication_package.zip byte size.")
    else:
        try:
            if int(expected_size) != actual_size:
                audit.error(f"publication_package.zip byte size {actual_size} does not match final_archive_manifest.json {expected_size}.")
        except (TypeError, ValueError):
            audit.error(f"Invalid ZIP byte size in final_archive_manifest.json: {expected_size!r}.")
    if expected_sha is None:
        audit.error("final_archive_manifest.json does not record publication_package.zip SHA256.")
    elif str(expected_sha).lower() != actual_sha:
        audit.error("publication_package.zip SHA256 does not match final_archive_manifest.json.")


def audit_package_manifest(audit: Audit) -> None:
    manifest_path = ROOT_PACKAGE_MANIFEST if ROOT_PACKAGE_MANIFEST.exists() else PACKAGED_PACKAGE_MANIFEST
    manifest = load_json(manifest_path, audit)
    entries = package_manifest_entries(manifest)
    if not entries:
        audit.error(f"Package manifest has no recognizable file entries: {rel(manifest_path)}")
        return
    if not PACKAGE_ZIP.exists():
        return
    try:
        with zipfile.ZipFile(PACKAGE_ZIP, "r") as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
            for entry in entries:
                path = entry_path(entry)
                if not path:
                    audit.error(f"Package manifest entry lacks a path: {entry}")
                    continue
                if path not in names and f"publication_package/{path}" not in names:
                    audit.error(f"Manifest-listed file is absent from publication_package.zip: {path}")
    except zipfile.BadZipFile:
        audit.error("publication_package.zip is not a valid ZIP archive.")
    except OSError as exc:
        audit.error(f"Cannot inspect publication_package.zip: {exc}")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    passed = not audit.errors and not audit.warnings
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "notes": audit.notes,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Submission artifact consistency audit",
        "====================================",
        "",
        f"Passed: {passed}",
        f"Errors: {len(audit.errors)}",
        f"Warnings: {len(audit.warnings)}",
        "",
        "Errors",
        "------",
        *(f"- {item}" for item in audit.errors),
        "",
        "Warnings",
        "--------",
        *(f"- {item}" for item in audit.warnings),
        "",
        "Notes",
        "-----",
        *(f"- {item}" for item in audit.notes),
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    audit_text_html_consistency(audit)
    audit_completion_status(audit)
    audit_audit_logs(audit)
    audit_archive_manifest(audit)
    audit_package_manifest(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if not audit.errors and not audit.warnings else 1


if __name__ == "__main__":
    sys.exit(main())

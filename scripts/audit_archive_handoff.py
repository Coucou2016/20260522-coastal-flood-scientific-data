from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
MANUSCRIPT_DIR = ROOT / "manuscript"
PACKAGE_ZIP = ROOT / "publication_package.zip"
FINAL_ARCHIVE_MANIFEST = ROOT / "final_archive_manifest.json"
EVIDENCE_DIR = ROOT / "publication_gate_evidence"
EVIDENCE_MANIFEST = EVIDENCE_DIR / "evidence_manifest.json"
EVIDENCE_MANIFEST_SHA256 = EVIDENCE_DIR / "evidence_manifest.sha256"
REPORT_TXT = LOG_DIR / "archive_handoff_audit.txt"
REPORT_JSON = LOG_DIR / "archive_handoff_audit.json"

REQUIRED_SIDECARS = [
    FINAL_ARCHIVE_MANIFEST,
    EVIDENCE_MANIFEST,
    EVIDENCE_MANIFEST_SHA256,
    EVIDENCE_DIR / "publication_gate.txt",
    EVIDENCE_DIR / "publication_gate.json",
    EVIDENCE_DIR / "publication_readiness_summary.md",
    EVIDENCE_DIR / "publication_readiness_summary.json",
    EVIDENCE_DIR / "manuscript_figure_inventory.md",
    EVIDENCE_DIR / "figure_deliverables_audit.txt",
    EVIDENCE_DIR / "figure_visual_quality_audit.txt",
    EVIDENCE_DIR / "figure_data_integrity_audit.txt",
    EVIDENCE_DIR / "manuscript_submission_text_audit.txt",
    EVIDENCE_DIR / "submission_artifact_consistency_audit.txt",
    EVIDENCE_DIR / "final_qc_acceptance_audit.txt",
    MANUSCRIPT_DIR / "final_qc_acceptance.json",
    ROOT / "requirements-publication.txt",
]

FORBIDDEN_ZIP_NAMES = {
    "final_archive_manifest.json",
    "publication_gate_evidence/evidence_manifest.json",
    "publication_gate_evidence/publication_gate.txt",
    "publication_gate_evidence/publication_gate.json",
}


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_sidecars: list[str] = field(default_factory=list)
    zip_entries_checked: int = 0

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, audit: Audit, required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            audit.errors.append(f"Missing required JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        audit.errors.append(f"Invalid JSON in {rel(path)}: {exc}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_sidecars(audit: Audit) -> None:
    for path in REQUIRED_SIDECARS:
        audit.checked_sidecars.append(rel(path))
        if not path.exists():
            audit.errors.append(f"Missing required archive sidecar/evidence file: {rel(path)}")

    evidence = load_json(EVIDENCE_MANIFEST, audit, required=False)
    if isinstance(evidence, dict):
        if evidence.get("passed") is not True:
            audit.errors.append("publication_gate_evidence/evidence_manifest.json does not record passed=true.")
        files = evidence.get("files")
        if not isinstance(files, list) or not files:
            audit.errors.append("publication_gate_evidence/evidence_manifest.json has no files list.")
    if EVIDENCE_MANIFEST.exists() and EVIDENCE_MANIFEST_SHA256.exists():
        try:
            parts = EVIDENCE_MANIFEST_SHA256.read_text(encoding="utf-8").split()
        except OSError as exc:
            audit.errors.append(f"Cannot read {rel(EVIDENCE_MANIFEST_SHA256)}: {exc}")
        else:
            if len(parts) != 2:
                audit.errors.append("publication_gate_evidence/evidence_manifest.sha256 must contain '<sha256>  evidence_manifest.json'.")
                return
            expected, target = parts[0].lower(), parts[1]
            if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
                audit.errors.append("publication_gate_evidence/evidence_manifest.sha256 does not contain a valid SHA256 digest.")
                return
            if target.replace("\\", "/") != "evidence_manifest.json":
                audit.errors.append("publication_gate_evidence/evidence_manifest.sha256 must target evidence_manifest.json.")
                return
            actual = sha256_file(EVIDENCE_MANIFEST)
            if expected != actual:
                audit.errors.append("publication_gate_evidence/evidence_manifest.sha256 does not match evidence_manifest.json.")


def audit_zip_boundary(audit: Audit) -> None:
    if not PACKAGE_ZIP.exists():
        audit.errors.append("publication_package.zip is missing.")
        return
    try:
        with zipfile.ZipFile(PACKAGE_ZIP, "r") as archive:
            names = {name.replace("\\", "/").lstrip("./") for name in archive.namelist()}
    except zipfile.BadZipFile:
        audit.errors.append("publication_package.zip is not a valid ZIP archive.")
        return
    except OSError as exc:
        audit.errors.append(f"Cannot inspect publication_package.zip: {exc}")
        return
    audit.zip_entries_checked = len(names)
    for forbidden in sorted(FORBIDDEN_ZIP_NAMES):
        if forbidden in names or f"publication_package/{forbidden}" in names:
            audit.errors.append(f"Archive contains sidecar/evidence file that should remain outside ZIP: {forbidden}")
    if not any(name.endswith("process_terrain_coastal_flood_CEE_manuscript_review.html") for name in names):
        audit.errors.append("Archive does not contain the manuscript review HTML.")
    if not any(name.endswith("process_terrain_coastal_flood_CEE_manuscript.md") for name in names):
        audit.errors.append("Archive does not contain the manuscript Markdown.")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "checked_sidecars": audit.checked_sidecars,
                "zip_entries_checked": audit.zip_entries_checked,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Archive Handoff Audit",
        "=====================",
        "",
        f"Passed: {audit.passed}",
        f"Sidecars checked: {len(audit.checked_sidecars)}",
        f"ZIP entries checked: {audit.zip_entries_checked}",
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
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    audit_sidecars(audit)
    audit_zip_boundary(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())

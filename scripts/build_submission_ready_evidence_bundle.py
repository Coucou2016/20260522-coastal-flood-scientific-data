"""Build the final submission-ready evidence bundle.

The core publication gate has its own evidence bundle. This script creates a
submission-level evidence bundle that also includes the final figure/data
sign-off audit and the combined submission-ready report.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "submission_ready_gate_evidence"
LOGS_DIR = ROOT / "logs"

MANIFEST = DEST / "evidence_manifest.json"
MANIFEST_SHA256 = DEST / "evidence_manifest.sha256"

EVIDENCE_FILES = [
    ROOT / "PUBLICATION_GATE_TERMINAL_RUN.md",
    ROOT / "publication_gate_evidence" / "evidence_manifest.json",
    ROOT / "publication_gate_evidence" / "evidence_manifest.sha256",
    ROOT / "manuscript" / "final_figure_data_signoff.json",
    ROOT / "manuscript" / "final_figure_data_signoff.md",
    ROOT / "manuscript" / "final_figure_data_issue_register.json",
    ROOT / "manuscript" / "final_figure_data_issue_register.md",
    ROOT / "manuscript" / "final_figure_data_review_matrix.json",
    ROOT / "manuscript" / "final_figure_data_review_matrix.md",
    ROOT / "manuscript" / "final_figure_data_review_matrix_template.json",
    LOGS_DIR / "submission_ready_gate_scripts_audit.md",
    LOGS_DIR / "submission_ready_gate_scripts_audit.json",
    LOGS_DIR / "publication_gate_report.md",
    LOGS_DIR / "publication_gate_report.json",
    LOGS_DIR / "final_figure_data_review_matrix_template.md",
    LOGS_DIR / "final_figure_data_review_matrix_template.json",
    LOGS_DIR / "final_figure_data_review_matrix_audit.md",
    LOGS_DIR / "final_figure_data_review_matrix_audit.json",
    LOGS_DIR / "final_figure_data_issue_register_audit.md",
    LOGS_DIR / "final_figure_data_issue_register_audit.json",
    LOGS_DIR / "final_figure_data_signoff_audit.md",
    LOGS_DIR / "final_figure_data_signoff_audit.json",
    ROOT / "publication_package.zip",
    ROOT / "final_archive_manifest.json",
]


def clean_bundle_dir() -> None:
    """Remove stale submission-ready bundle contents before rebuilding."""
    if not DEST.exists():
        return
    for item in DEST.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_evidence() -> dict:
    clean_bundle_dir()
    DEST.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    missing: list[str] = []

    for source in EVIDENCE_FILES:
        rel = source.relative_to(ROOT)
        if not source.exists():
            missing.append(str(rel))
            continue

        source_size = source.stat().st_size
        source_sha256 = sha256_file(source)
        target_name = str(rel).replace("\\", "__").replace("/", "__")
        target = DEST / target_name
        shutil.copy2(source, target)
        entries.append(
            {
                "source": str(rel),
                "source_bytes": source_size,
                "source_sha256": source_sha256,
                "bundle_file": target.name,
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )

    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not missing,
        "bundle": str(DEST.relative_to(ROOT)),
        "missing": missing,
        "entries": entries,
    }


def main() -> int:
    manifest = copy_evidence()
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = sha256_file(MANIFEST)
    MANIFEST_SHA256.write_text(f"{digest}  evidence_manifest.json\n", encoding="utf-8")
    print(f"Passed: {manifest['passed']}")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the final handoff evidence bundle.

This bundle captures the evidence available after the submission-ready gate and
terminal-run record audit have completed. It intentionally excludes the final
handoff report itself, because that report is generated after this bundle is
audited.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
DEST = ROOT / "final_submission_handoff_evidence"

MANIFEST = DEST / "evidence_manifest.json"
MANIFEST_SHA256 = DEST / "evidence_manifest.sha256"

EVIDENCE_FILES = [
    ROOT / "PUBLICATION_GATE_TERMINAL_RUN.md",
    ROOT / "publication_package.zip",
    ROOT / "final_archive_manifest.json",
    ROOT / "submission_ready_gate_evidence" / "evidence_manifest.json",
    ROOT / "submission_ready_gate_evidence" / "evidence_manifest.sha256",
    ROOT / "manuscript" / "submission_ready_terminal_run_record.json",
    ROOT / "manuscript" / "submission_ready_terminal_run_record.md",
    LOGS_DIR / "submission_ready_gate_report.md",
    LOGS_DIR / "submission_ready_gate_report.json",
    LOGS_DIR / "submission_ready_failure_summary.md",
    LOGS_DIR / "submission_ready_failure_summary.json",
    LOGS_DIR / "submission_ready_evidence_bundle_audit.md",
    LOGS_DIR / "submission_ready_evidence_bundle_audit.json",
    LOGS_DIR / "submission_ready_terminal_run_record_audit.md",
    LOGS_DIR / "submission_ready_terminal_run_record_audit.json",
]


def clean_bundle_dir() -> None:
    """Remove stale bundle contents before writing a new final handoff bundle."""
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


def main() -> int:
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
        bundle_name = str(rel).replace("\\", "__").replace("/", "__")
        target = DEST / bundle_name
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

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not missing,
        "bundle": str(DEST.relative_to(ROOT)),
        "missing": missing,
        "entries": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_SHA256.write_text(f"{sha256_file(MANIFEST)}  evidence_manifest.json\n", encoding="utf-8")

    print(f"Passed: {manifest['passed']}")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

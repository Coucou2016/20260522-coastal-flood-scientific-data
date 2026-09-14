from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "publication_package"
PACKAGE_ZIP = ROOT / "publication_package.zip"
MANIFEST = PACKAGE_DIR / "package_manifest.json"
STATUS = PACKAGE_DIR / "completion_status.json"
FINAL_ARCHIVE_MANIFEST = ROOT / "final_archive_manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]):
    if not path.exists():
        add_error(errors, f"Missing JSON file: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        add_error(errors, f"Could not parse JSON {path}: {exc}")
        return None


def validate_status(errors: list[str]) -> None:
    status = load_json(STATUS, errors)
    if not isinstance(status, dict):
        return
    if status.get("status") != "finalized":
        add_error(errors, f"completion_status.json status is not finalized: {status.get('status')!r}")
    for key in ["finalization_report", "standalone_html", "package_zip", "audit_expected"]:
        if not status.get(key):
            add_error(errors, f"completion_status.json missing key: {key}")
    if status.get("audit_expected") != "PUBLICATION READINESS AUDIT: PASS":
        add_error(errors, "completion_status.json does not require PUBLICATION READINESS AUDIT: PASS")


def validate_manifest(errors: list[str]) -> set[str]:
    manifest = load_json(MANIFEST, errors)
    if not isinstance(manifest, dict):
        return set()
    files = manifest.get("files")
    if not isinstance(files, list):
        add_error(errors, "package_manifest.json has no files list")
        return set()
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            add_error(errors, f"Invalid manifest entry: {entry!r}")
            continue
        rel = entry.get("path")
        if not isinstance(rel, str) or not rel:
            add_error(errors, f"Manifest entry missing path: {entry!r}")
            continue
        if rel in seen:
            add_error(errors, f"Duplicate manifest path: {rel}")
        seen.add(rel)
        path = PACKAGE_DIR / rel
        if not path.exists():
            add_error(errors, f"Manifest file missing from package: {rel}")
            continue
        if rel == "package_manifest.json":
            if entry.get("bytes") is not None or entry.get("sha256") is not None:
                add_error(errors, "Self-referential package_manifest.json should omit bytes and sha256")
            continue
        if entry.get("bytes") != path.stat().st_size:
            add_error(errors, f"Manifest byte size mismatch for {rel}")
        expected_hash = entry.get("sha256")
        if expected_hash != sha256(path):
            add_error(errors, f"Manifest sha256 mismatch for {rel}")
    for required in [
        "README.md",
        "package_manifest.json",
        "completion_status.json",
        "manuscript/process_terrain_coastal_flood_CEE_manuscript.md",
        "manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html",
        "manuscript/publication_readiness_report.md",
        "figures/main/Fig4_deltadtm_terrain_sensitivity.png",
        "figures/main/Fig5_process_terrain_typology.png",
        "data/figure_source/Fig4_connected_terrain_sensitivity.csv",
        "data/figure_source/Fig5_process_terrain_typology.csv",
    ]:
        if required not in seen:
            add_error(errors, f"Required package member missing from manifest: {required}")
    return seen


def validate_zip(manifest_members: set[str], errors: list[str]) -> None:
    if not PACKAGE_ZIP.exists():
        add_error(errors, f"Missing archive: {PACKAGE_ZIP}")
        return
    if PACKAGE_ZIP.stat().st_size < 100_000:
        add_error(errors, f"Archive is suspiciously small: {PACKAGE_ZIP.stat().st_size} bytes")
    try:
        with zipfile.ZipFile(PACKAGE_ZIP, "r") as zf:
            bad = zf.testzip()
            if bad:
                add_error(errors, f"Zip archive failed CRC check at: {bad}")
            names = set(zf.namelist())
    except Exception as exc:  # noqa: BLE001
        add_error(errors, f"Could not read zip archive: {exc}")
        return
    expected = {f"publication_package/{rel}" for rel in manifest_members}
    missing = sorted(expected - names)
    if missing:
        add_error(errors, "Zip archive missing manifest-listed files: " + ", ".join(missing[:20]))


def validate_final_archive_manifest(errors: list[str]) -> None:
    manifest = load_json(FINAL_ARCHIVE_MANIFEST, errors)
    if not isinstance(manifest, dict):
        add_error(errors, "final_archive_manifest.json is expected at the project root, outside publication_package.zip, to avoid self-referential archive hashing.")
        return
    if manifest.get("archive") != "publication_package.zip":
        add_error(errors, "final_archive_manifest.json archive should be publication_package.zip")
    if not PACKAGE_ZIP.exists():
        add_error(errors, "Cannot validate final_archive_manifest.json because publication_package.zip is missing")
        return
    if manifest.get("bytes") != PACKAGE_ZIP.stat().st_size:
        add_error(errors, "final_archive_manifest.json byte size does not match publication_package.zip")
    if manifest.get("sha256") != sha256(PACKAGE_ZIP):
        add_error(errors, "final_archive_manifest.json sha256 does not match publication_package.zip")
    if manifest.get("validation_log") != "logs/final_archive_validation.txt":
        add_error(errors, "final_archive_manifest.json validation_log should point to logs/final_archive_validation.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a finalized publication_package directory and zip archive.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    if not PACKAGE_DIR.exists():
        add_error(errors, f"Missing package directory: {PACKAGE_DIR}")
    validate_status(errors)
    members = validate_manifest(errors)
    validate_zip(members, errors)
    validate_final_archive_manifest(errors)
    if errors:
        if not args.quiet:
            print("PUBLICATION PACKAGE VALIDATION: FAIL")
            for err in errors:
                print(f"- {err}")
        return 1
    if not args.quiet:
        print("PUBLICATION PACKAGE VALIDATION: PASS")
        print(f"Validated {len(members)} package files and archive {PACKAGE_ZIP}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
SUMMARY_MD = LOG_DIR / "publication_readiness_summary.md"
SUMMARY_JSON = LOG_DIR / "publication_readiness_summary.json"

PACKAGE_ZIP = ROOT / "publication_package.zip"
COMPLETION_STATUS = ROOT / "completion_status.json"
FINAL_ARCHIVE_MANIFEST = ROOT / "final_archive_manifest.json"


@dataclass
class Check:
    name: str
    passed: bool
    evidence: str
    detail: str = ""


@dataclass
class Summary:
    checks: list[Check] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.blockers and all(check.passed for check in self.checks)

    def add(self, name: str, passed: bool, evidence: Path | str, detail: str = "") -> None:
        evidence_text = str(evidence.relative_to(ROOT)) if isinstance(evidence, Path) else evidence
        self.checks.append(Check(name=name, passed=passed, evidence=evidence_text, detail=detail))
        if not passed:
            self.blockers.append(f"{name}: {detail or evidence_text}")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing {path.relative_to(ROOT)}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.relative_to(ROOT)}: {exc}"
    except OSError as exc:
        return None, f"cannot read {path.relative_to(ROOT)}: {exc}"


def read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return "", f"missing {path.relative_to(ROOT)}"
    except OSError as exc:
        return "", f"cannot read {path.relative_to(ROOT)}: {exc}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_audit_passed(path: Path) -> tuple[bool, str]:
    data, error = load_json(path)
    if error:
        return False, error
    if not isinstance(data, dict):
        return False, f"{path.relative_to(ROOT)} is not a JSON object"
    errors = data.get("errors") or []
    warnings = data.get("warnings") or []
    passed = data.get("passed")
    if passed is False:
        return False, "reported passed=false"
    if errors:
        return False, f"reports {len(errors)} error(s)"
    if warnings:
        return False, f"reports {len(warnings)} warning(s)"
    return True, "passed with no errors or warnings"


def figure_inventory_passed(path: Path) -> tuple[bool, str]:
    data, error = load_json(path)
    if error:
        return False, error
    if not isinstance(data, dict):
        return False, f"{path.relative_to(ROOT)} is not a JSON object"
    if data.get("passed") is False:
        return False, "reported passed=false"
    image_count = data.get("image_count")
    error_count = data.get("error_count")
    records = data.get("records")
    if not isinstance(image_count, int) or image_count <= 0:
        return False, "does not record any manuscript images"
    if error_count != 0:
        return False, f"reports {error_count} image error(s)"
    if not isinstance(records, list) or len(records) != image_count:
        return False, "record count does not match image_count"
    return True, f"{image_count} manuscript image record(s), no inventory errors"


def text_validation_passed(path: Path) -> tuple[bool, str]:
    text, error = read_text(path)
    if error:
        return False, error
    failure_patterns = [
        r"(?m)^\s*(?:failed|error|errors|exception|traceback)\b",
        r"\btraceback \(most recent call last\)",
        r"\bvalidation failed\b",
        r"\bfailed with exit code\s+[1-9]\d*\b",
        r"\berrors?\s*:\s*[1-9]\d*\b",
        r"\bfailed\s*:\s*[1-9]\d*\b",
    ]
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in failure_patterns):
        return False, "contains failure wording"
    return True, "no failure wording detected"


def archive_zip_info(manifest: dict[str, Any]) -> dict[str, Any] | None:
    for key in ["publication_package_zip", "publication_package.zip", "zip", "archive", "final_archive"]:
        value = manifest.get(key)
        if isinstance(value, dict):
            return value
    for value in manifest.values():
        if isinstance(value, dict) and any(key in value for key in ["sha256", "zip_sha256", "bytes", "size_bytes"]):
            return value
    return None


def first_present(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def check_archive_manifest(summary: Summary) -> None:
    manifest, error = load_json(FINAL_ARCHIVE_MANIFEST)
    if error:
        summary.add("Final archive manifest", False, FINAL_ARCHIVE_MANIFEST, error)
        return
    if not isinstance(manifest, dict):
        summary.add("Final archive manifest", False, FINAL_ARCHIVE_MANIFEST, "not a JSON object")
        return
    if not PACKAGE_ZIP.exists():
        summary.add("Final archive manifest", False, PACKAGE_ZIP, "publication_package.zip is missing")
        return
    zip_info = archive_zip_info(manifest)
    if zip_info is None:
        summary.add("Final archive manifest", False, FINAL_ARCHIVE_MANIFEST, "missing ZIP metadata")
        return
    expected_size = first_present(zip_info, ["bytes", "size", "size_bytes", "zip_bytes", "archive_bytes"])
    expected_sha = first_present(zip_info, ["sha256", "zip_sha256", "archive_sha256", "publication_package_zip_sha256"])
    if expected_size is None or expected_sha is None:
        summary.add("Final archive manifest", False, FINAL_ARCHIVE_MANIFEST, "missing ZIP size or SHA256")
        return
    actual_size = PACKAGE_ZIP.stat().st_size
    actual_sha = sha256_file(PACKAGE_ZIP)
    try:
        expected_size_int = int(expected_size)
    except (TypeError, ValueError):
        summary.add("Final archive manifest", False, FINAL_ARCHIVE_MANIFEST, f"invalid ZIP byte size {expected_size!r}")
        return
    passed = expected_size_int == actual_size and str(expected_sha).lower() == actual_sha
    detail = "ZIP size and SHA256 match final_archive_manifest.json" if passed else "ZIP size or SHA256 mismatch"
    summary.add("Final archive manifest", passed, FINAL_ARCHIVE_MANIFEST, detail)


def build_summary() -> Summary:
    summary = Summary()

    completion, error = load_json(COMPLETION_STATUS)
    completion_ok = isinstance(completion, dict) and completion.get("status") == "finalized"
    summary.add(
        "Completion status",
        completion_ok,
        COMPLETION_STATUS,
        "status=finalized" if completion_ok else (error or "status is not finalized"),
    )

    inventory_passed, inventory_detail = figure_inventory_passed(LOG_DIR / "manuscript_figure_inventory.json")
    summary.add("Manuscript figure inventory", inventory_passed, LOG_DIR / "manuscript_figure_inventory.json", inventory_detail)

    for name, path in [
        ("Publication gate scripts audit", LOG_DIR / "publication_gate_scripts_audit.json"),
        ("Python runtime dependencies audit", LOG_DIR / "python_runtime_dependencies_audit.json"),
        ("Figure deliverables audit", LOG_DIR / "figure_deliverables_audit.json"),
        ("Figure visual-quality audit", LOG_DIR / "figure_visual_quality_audit.json"),
        ("Manual figure review sheet", LOG_DIR / "manual_figure_review_sheet.json"),
        ("Figure/source-data audit", LOG_DIR / "figure_data_integrity_audit.json"),
        ("Manuscript submission text audit", LOG_DIR / "manuscript_submission_text_audit.json"),
        ("Reference metadata audit", LOG_DIR / "reference_metadata_audit.json"),
        ("Journal submission metadata audit", LOG_DIR / "journal_submission_metadata_audit.json"),
        ("Submission artifact consistency audit", LOG_DIR / "submission_artifact_consistency_audit.json"),
        ("Final QC acceptance audit", LOG_DIR / "final_qc_acceptance_audit.json"),
        ("Repository deposit readiness audit", LOG_DIR / "repository_deposit_readiness_audit.json"),
    ]:
        passed, detail = json_audit_passed(path)
        summary.add(name, passed, path, detail)

    for name, path in [
        ("Publication package validation", LOG_DIR / "publication_package_validation.txt"),
        ("Final archive validation", LOG_DIR / "final_archive_validation.txt"),
    ]:
        passed, detail = text_validation_passed(path)
        summary.add(name, passed, path, detail)

    archive_handoff = LOG_DIR / "archive_handoff_audit.json"
    if archive_handoff.exists():
        passed, detail = json_audit_passed(archive_handoff)
        summary.add("Archive handoff audit", passed, archive_handoff, detail)

    check_archive_manifest(summary)
    return summary


def write_summary(summary: Summary) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "created_utc": now_utc(),
        "passed": summary.passed,
        "blockers": summary.blockers,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "evidence": check.evidence,
                "detail": check.detail,
            }
            for check in summary.checks
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "Publication Readiness Summary",
        "=============================",
        "",
        f"Created UTC: {data['created_utc']}",
        f"Passed: {summary.passed}",
        "",
        "Checks",
        "------",
    ]
    for check in summary.checks:
        status = "PASS" if check.passed else "FAIL"
        detail = f" - {check.detail}" if check.detail else ""
        lines.append(f"- {status}: {check.name} ({check.evidence}){detail}")
    lines.extend(["", "Blockers", "--------"])
    if summary.blockers:
        lines.extend(f"- {item}" for item in summary.blockers)
    else:
        lines.append("- None")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    summary = build_summary()
    write_summary(summary)
    print(SUMMARY_MD.relative_to(ROOT))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    sys.exit(main())

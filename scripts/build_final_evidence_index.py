from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
MANUSCRIPT_DIR = ROOT / "manuscript"
EVIDENCE_DIR = ROOT / "publication_gate_evidence"
REPORT_MD = LOG_DIR / "final_evidence_index.md"
REPORT_JSON = LOG_DIR / "final_evidence_index.json"


@dataclass
class EvidenceItem:
    role: str
    path: Path
    kind: str
    required: bool = True
    contextual: bool = False


@dataclass
class EvidenceStatus:
    role: str
    path: str
    kind: str
    required: bool
    contextual: bool
    present: bool
    passed: bool
    detail: str = ""


@dataclass
class Index:
    statuses: list[EvidenceStatus] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings and all(
            status.passed for status in self.statuses if status.required and not status.contextual
        )


EVIDENCE_ITEMS = [
    EvidenceItem("Gate report", LOG_DIR / "publication_gate.txt", "text", contextual=True),
    EvidenceItem("Gate report JSON", LOG_DIR / "publication_gate.json", "json", contextual=True),
    EvidenceItem("Completion status", ROOT / "completion_status.json", "json"),
    EvidenceItem("Publication runtime requirements", ROOT / "requirements-publication.txt", "text"),
    EvidenceItem("Python wrapper entrypoint", ROOT / "scripts" / "run_python_checked.cmd", "text"),
    EvidenceItem("Environment diagnostics helper", ROOT / "scripts" / "diagnose_publication_environment.cmd", "text"),
    EvidenceItem("Requirements install helper", ROOT / "scripts" / "install_publication_requirements.cmd", "text"),
    EvidenceItem("Package manifest", ROOT / "package_manifest.json", "json", required=False),
    EvidenceItem("Packaged manifest", ROOT / "publication_package" / "package_manifest.json", "json", required=False),
    EvidenceItem("Final archive manifest", ROOT / "final_archive_manifest.json", "json"),
    EvidenceItem("Publication ZIP", ROOT / "publication_package.zip", "file"),
    EvidenceItem("Gate scripts audit", LOG_DIR / "publication_gate_scripts_audit.json", "json"),
    EvidenceItem("Environment diagnostics log", LOG_DIR / "publication_environment_diagnostics.txt", "text", contextual=True),
    EvidenceItem("Python runtime dependencies audit", LOG_DIR / "python_runtime_dependencies_audit.json", "json"),
    EvidenceItem("Figure inventory", LOG_DIR / "manuscript_figure_inventory.json", "json"),
    EvidenceItem("Figure deliverables audit", LOG_DIR / "figure_deliverables_audit.json", "json"),
    EvidenceItem("Figure visual-quality audit", LOG_DIR / "figure_visual_quality_audit.json", "json"),
    EvidenceItem("Manual figure review sheet", LOG_DIR / "manual_figure_review_sheet.json", "json"),
    EvidenceItem("Figure/source-data audit", LOG_DIR / "figure_data_integrity_audit.json", "json"),
    EvidenceItem("Manuscript text audit", LOG_DIR / "manuscript_submission_text_audit.json", "json"),
    EvidenceItem("Reference metadata audit", LOG_DIR / "reference_metadata_audit.json", "json"),
    EvidenceItem("Journal submission metadata audit", LOG_DIR / "journal_submission_metadata_audit.json", "json"),
    EvidenceItem("Artifact consistency audit", LOG_DIR / "submission_artifact_consistency_audit.json", "json"),
    EvidenceItem("Final QC acceptance audit", LOG_DIR / "final_qc_acceptance_audit.json", "json"),
    EvidenceItem("Repository deposit readiness audit", LOG_DIR / "repository_deposit_readiness_audit.json", "json"),
    EvidenceItem("Package validation log", LOG_DIR / "publication_package_validation.txt", "text"),
    EvidenceItem("Final archive validation log", LOG_DIR / "final_archive_validation.txt", "text"),
    EvidenceItem("Archive handoff audit", LOG_DIR / "archive_handoff_audit.json", "json"),
    EvidenceItem("Publication readiness summary", LOG_DIR / "publication_readiness_summary.json", "json"),
    EvidenceItem("Final QC acceptance record", MANUSCRIPT_DIR / "final_qc_acceptance.json", "json"),
    EvidenceItem("Gate evidence manifest", EVIDENCE_DIR / "evidence_manifest.json", "json", contextual=True),
    EvidenceItem("Gate evidence manifest SHA256 sidecar", EVIDENCE_DIR / "evidence_manifest.sha256", "text", contextual=True),
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


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


def json_status(item: EvidenceItem) -> tuple[bool, str]:
    try:
        data = json.loads(item.path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON: {exc}"
    except OSError as exc:
        return False, f"cannot read JSON: {exc}"
    if not isinstance(data, dict):
        return False, "JSON root is not an object"
    errors = data.get("errors") or []
    warnings = data.get("warnings") or []
    if errors:
        return False, f"reports {len(errors)} error(s)"
    if warnings:
        return False, f"reports {len(warnings)} warning(s)"
    if data.get("passed") is False:
        return False, "reports passed=false"
    if item.path == ROOT / "completion_status.json" and data.get("status") != "finalized":
        return False, "completion status is not finalized"
    return True, "ok"


def text_status(item: EvidenceItem) -> tuple[bool, str]:
    try:
        text = item.path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return False, f"cannot read text: {exc}"
    if validation_text_has_failure(text):
        return False, "contains failure wording"
    return True, "ok"


def file_status(item: EvidenceItem) -> tuple[bool, str]:
    try:
        size = item.path.stat().st_size
    except OSError as exc:
        return False, f"cannot stat file: {exc}"
    if size <= 0:
        return False, "file is empty"
    return True, f"{size} bytes"


def evaluate_item(item: EvidenceItem) -> EvidenceStatus:
    present = item.path.exists()
    if not present:
        return EvidenceStatus(item.role, rel(item.path), item.kind, item.required, item.contextual, False, not item.required, "missing")
    if item.kind == "json":
        passed, detail = json_status(item)
    elif item.kind == "text":
        passed, detail = text_status(item)
    else:
        passed, detail = file_status(item)
    return EvidenceStatus(item.role, rel(item.path), item.kind, item.required, item.contextual, True, passed, detail)


def build_index() -> Index:
    index = Index()
    for item in EVIDENCE_ITEMS:
        status = evaluate_item(item)
        index.statuses.append(status)
        if item.contextual:
            continue
        if item.required and not status.present:
            index.errors.append(f"Missing required evidence: {status.path}")
        elif item.required and not status.passed:
            index.errors.append(f"Required evidence did not pass: {status.path} ({status.detail})")

    root_manifest = ROOT / "package_manifest.json"
    packaged_manifest = ROOT / "publication_package" / "package_manifest.json"
    if not root_manifest.exists() and not packaged_manifest.exists():
        index.errors.append("Missing package_manifest.json at project root or inside publication_package/.")
    return index


def write_index(index: Index) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": index.passed,
                "errors": index.errors,
                "warnings": index.warnings,
                "self_outputs": [
                    rel(REPORT_MD),
                    rel(REPORT_JSON),
                ],
                "evidence": [status.__dict__ for status in index.statuses],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Final Evidence Index",
        "====================",
        "",
        f"Passed: {index.passed}",
        f"Evidence items: {len(index.statuses)}",
        f"Errors: {len(index.errors)}",
        f"Warnings: {len(index.warnings)}",
        "",
        "Self Outputs",
        "------------",
        f"- {rel(REPORT_MD)}",
        f"- {rel(REPORT_JSON)}",
        "",
        "| Role | Path | Required | Contextual | Present | Passed | Detail |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for status in index.statuses:
        lines.append(
            f"| {status.role} | {status.path} | {status.required} | {status.contextual} | "
            f"{status.present} | {status.passed} | {status.detail} |"
        )
    lines.extend(["", "Errors", "------"])
    lines.extend(f"- {item}" for item in index.errors)
    lines.extend(["", "Warnings", "--------"])
    lines.extend(f"- {item}" for item in index.warnings)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    index = build_index()
    write_index(index)
    print(REPORT_MD.relative_to(ROOT))
    return 0 if index.passed else 1


if __name__ == "__main__":
    sys.exit(main())

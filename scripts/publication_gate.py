from __future__ import annotations

import json
import hashlib
import subprocess
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "publication_gate.txt"
REPORT_JSON = LOG_DIR / "publication_gate.json"
REPORT_MD_ALIAS = LOG_DIR / "publication_gate_report.md"
REPORT_JSON_ALIAS = LOG_DIR / "publication_gate_report.json"
EVIDENCE_DIR = ROOT / "publication_gate_evidence"


@dataclass
class Step:
    name: str
    command: list[str]
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class GateReport:
    started_utc: str
    finished_utc: str | None = None
    steps: list[Step] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings and all(step.passed for step in self.steps)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_step(step: Step, report: GateReport) -> None:
    try:
        completed = subprocess.run(
            step.command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        step.returncode = -1
        step.stderr = str(exc)
        report.steps.append(step)
        report.errors.append(f"{step.name} could not be started: {exc}")
        return
    step.returncode = completed.returncode
    step.stdout = completed.stdout
    step.stderr = completed.stderr
    report.steps.append(step)
    if completed.returncode != 0:
        report.errors.append(f"{step.name} failed with exit code {completed.returncode}.")


def load_json(path: Path, report: GateReport) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.errors.append(f"Missing required file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        report.errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_if_present(source: Path, destination_dir: Path, copied: list[dict[str, object]]) -> None:
    if not source.exists() or source.is_dir():
        return
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    shutil.copy2(source, destination)
    copied.append(
        {
            "source": str(source.relative_to(ROOT)),
            "copy": str(destination.relative_to(ROOT)),
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        }
    )


def write_evidence_bundle(report: GateReport) -> None:
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, object]] = []
    package_manifest = ROOT / "package_manifest.json"
    packaged_manifest = ROOT / "publication_package" / "package_manifest.json"
    evidence_files = [
        ROOT / "completion_status.json",
        ROOT / "requirements-publication.txt",
        ROOT / "scripts" / "run_python_checked.cmd",
        ROOT / "scripts" / "diagnose_publication_environment.cmd",
        ROOT / "scripts" / "install_publication_requirements.cmd",
        MANUSCRIPT_DIR / "final_qc_acceptance.json",
        MANUSCRIPT_DIR / "final_qc_acceptance.md",
        package_manifest if package_manifest.exists() else packaged_manifest,
        ROOT / "final_archive_manifest.json",
        LOG_DIR / "publication_gate.txt",
        LOG_DIR / "publication_gate.json",
        LOG_DIR / "publication_environment_diagnostics.txt",
        LOG_DIR / "publication_gate_scripts_audit.txt",
        LOG_DIR / "publication_gate_scripts_audit.json",
        LOG_DIR / "python_runtime_dependencies_audit.txt",
        LOG_DIR / "python_runtime_dependencies_audit.json",
        LOG_DIR / "manuscript_figure_inventory.md",
        LOG_DIR / "manuscript_figure_inventory.json",
        LOG_DIR / "figure_deliverables_audit.txt",
        LOG_DIR / "figure_deliverables_audit.json",
        LOG_DIR / "figure_visual_quality_audit.txt",
        LOG_DIR / "figure_visual_quality_audit.json",
        LOG_DIR / "manual_figure_review_sheet.md",
        LOG_DIR / "manual_figure_review_sheet.json",
        LOG_DIR / "figure_data_integrity_audit.txt",
        LOG_DIR / "figure_data_integrity_audit.json",
        LOG_DIR / "manuscript_submission_text_audit.txt",
        LOG_DIR / "manuscript_submission_text_audit.json",
        LOG_DIR / "reference_metadata_audit.txt",
        LOG_DIR / "reference_metadata_audit.json",
        LOG_DIR / "journal_submission_metadata_audit.txt",
        LOG_DIR / "journal_submission_metadata_audit.json",
        LOG_DIR / "submission_artifact_consistency_audit.txt",
        LOG_DIR / "submission_artifact_consistency_audit.json",
        LOG_DIR / "final_qc_acceptance_audit.txt",
        LOG_DIR / "final_qc_acceptance_audit.json",
        LOG_DIR / "repository_deposit_readiness_audit.txt",
        LOG_DIR / "repository_deposit_readiness_audit.json",
        LOG_DIR / "archive_handoff_audit.txt",
        LOG_DIR / "archive_handoff_audit.json",
        LOG_DIR / "publication_readiness_summary.md",
        LOG_DIR / "publication_readiness_summary.json",
        LOG_DIR / "final_evidence_index.md",
        LOG_DIR / "final_evidence_index.json",
        LOG_DIR / "publication_package_validation.txt",
        LOG_DIR / "final_archive_validation.txt",
    ]
    for source in evidence_files:
        copy_if_present(source, EVIDENCE_DIR, copied)
    bundle_manifest = {
        "passed": report.passed,
        "created_utc": now_utc(),
        "manifest_sha256_sidecar": "publication_gate_evidence/evidence_manifest.sha256",
        "files": copied,
    }
    manifest_path = EVIDENCE_DIR / "evidence_manifest.json"
    manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "evidence_manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  evidence_manifest.json\n",
        encoding="utf-8",
    )


def archive_zip_info(manifest: dict[str, object]) -> dict[str, object] | None:
    for key in ["publication_package_zip", "publication_package.zip", "zip", "archive", "final_archive"]:
        value = manifest.get(key)
        if isinstance(value, dict):
            return value
    for value in manifest.values():
        if isinstance(value, dict) and any(name in value for name in ["sha256", "zip_sha256", "archive_sha256", "bytes", "size_bytes"]):
            return value
    return None


def first_present(mapping: dict[str, object], keys: list[str]) -> object | None:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def check_final_artifacts(report: GateReport) -> None:
    package_dir = ROOT / "publication_package"
    package_zip = ROOT / "publication_package.zip"
    completion = ROOT / "completion_status.json"
    package_manifest = ROOT / "package_manifest.json"
    packaged_manifest = package_dir / "package_manifest.json"
    archive_manifest = ROOT / "final_archive_manifest.json"
    figure_audit = LOG_DIR / "figure_data_integrity_audit.txt"
    gate_scripts_audit = LOG_DIR / "publication_gate_scripts_audit.txt"
    figure_inventory = LOG_DIR / "manuscript_figure_inventory.md"
    figure_deliverables_audit = LOG_DIR / "figure_deliverables_audit.txt"
    figure_visual_audit = LOG_DIR / "figure_visual_quality_audit.txt"
    manual_figure_review = LOG_DIR / "manual_figure_review_sheet.md"
    text_audit = LOG_DIR / "manuscript_submission_text_audit.txt"
    reference_audit = LOG_DIR / "reference_metadata_audit.txt"
    journal_metadata_audit = LOG_DIR / "journal_submission_metadata_audit.txt"
    consistency_audit = LOG_DIR / "submission_artifact_consistency_audit.txt"
    final_qc_acceptance_audit = LOG_DIR / "final_qc_acceptance_audit.txt"
    repository_deposit_audit = LOG_DIR / "repository_deposit_readiness_audit.txt"
    readiness_summary = LOG_DIR / "publication_readiness_summary.md"
    package_validation = LOG_DIR / "publication_package_validation.txt"
    archive_validation = LOG_DIR / "final_archive_validation.txt"
    runtime_dependencies_audit = LOG_DIR / "python_runtime_dependencies_audit.txt"

    for path in [
        package_dir,
        package_zip,
        completion,
        archive_manifest,
        gate_scripts_audit,
        runtime_dependencies_audit,
        figure_audit,
        figure_inventory,
        figure_deliverables_audit,
        figure_visual_audit,
        manual_figure_review,
        text_audit,
        reference_audit,
        journal_metadata_audit,
        consistency_audit,
        final_qc_acceptance_audit,
        repository_deposit_audit,
        readiness_summary,
        package_validation,
        archive_validation,
    ]:
        if not path.exists():
            report.errors.append(f"Missing required final artifact: {path.relative_to(ROOT)}")
    if not package_manifest.exists() and not packaged_manifest.exists():
        report.errors.append("Missing required final artifact: package_manifest.json")

    status = load_json(completion, report)
    if isinstance(status, dict) and status.get("status") != "finalized":
        report.errors.append("completion_status.json does not report finalized status.")

    manifest_path = package_manifest if package_manifest.exists() else packaged_manifest
    if manifest_path.exists():
        load_json(manifest_path, report)

    manifest = load_json(archive_manifest, report)
    if isinstance(manifest, dict):
        zip_info = archive_zip_info(manifest)
        if zip_info is None:
            report.errors.append("final_archive_manifest.json does not include ZIP archive metadata.")
        elif package_zip.exists():
            expected_size = first_present(zip_info, ["bytes", "size", "size_bytes", "zip_bytes", "archive_bytes"])
            actual_size = package_zip.stat().st_size
            if expected_size is None:
                report.errors.append("final_archive_manifest.json does not record the ZIP byte size.")
            else:
                try:
                    expected_size_int = int(expected_size)
                except (TypeError, ValueError):
                    report.errors.append(f"ZIP byte size in final_archive_manifest.json is not an integer: {expected_size!r}.")
                else:
                    if expected_size_int != actual_size:
                        report.errors.append(
                            "publication_package.zip size does not match final_archive_manifest.json "
                            f"({actual_size} != {expected_size})."
                        )
            expected_sha = first_present(zip_info, ["sha256", "zip_sha256", "archive_sha256", "publication_package_zip_sha256"])
            if expected_sha is None:
                report.errors.append("final_archive_manifest.json does not record the ZIP SHA256 hash.")
            else:
                actual_sha = sha256_file(package_zip)
                if str(expected_sha).lower() != actual_sha:
                    report.errors.append("publication_package.zip SHA256 does not match final_archive_manifest.json.")


def write_reports(report: GateReport) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report.finished_utc = now_utc()
    data = {
        "started_utc": report.started_utc,
        "finished_utc": report.finished_utc,
        "passed": report.passed,
        "errors": report.errors,
        "warnings": report.warnings,
        "steps": [
            {
                "name": step.name,
                "command": step.command,
                "returncode": step.returncode,
                "passed": step.passed,
                "stdout_tail": step.stdout[-4000:],
                "stderr_tail": step.stderr[-4000:],
            }
            for step in report.steps
        ],
    }
    json_text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    REPORT_JSON.write_text(json_text, encoding="utf-8")
    REPORT_JSON_ALIAS.write_text(json_text, encoding="utf-8")

    lines = [
        "Publication gate",
        "================",
        "",
        f"Started UTC: {report.started_utc}",
        f"Finished UTC: {report.finished_utc}",
        f"Passed: {report.passed}",
        "",
        "Steps",
        "-----",
    ]
    for step in report.steps:
        lines.append(f"- {step.name}: exit {step.returncode}")
    lines.extend(["", "Errors", "------"])
    lines.extend(f"- {item}" for item in report.errors)
    lines.extend(["", "Warnings", "--------"])
    lines.extend(f"- {item}" for item in report.warnings)
    report_text = "\n".join(lines) + "\n"
    REPORT_TXT.write_text(report_text, encoding="utf-8")
    REPORT_MD_ALIAS.write_text(report_text, encoding="utf-8")
    write_evidence_bundle(report)


def main() -> int:
    report = GateReport(started_utc=now_utc())
    steps = [
        Step("publication gate scripts audit", ["cmd", "/c", "scripts\\run_publication_gate_scripts_audit.cmd"]),
        Step("Python runtime dependencies audit", ["cmd", "/c", "scripts\\run_python_runtime_dependencies_audit.cmd"]),
        Step("finalization", ["cmd", "/c", "scripts\\run_finalization.cmd"]),
        Step("manuscript figure inventory", ["cmd", "/c", "scripts\\run_manuscript_figure_inventory.cmd"]),
        Step("figure deliverables audit", ["cmd", "/c", "scripts\\run_figure_deliverables_audit.cmd"]),
        Step("figure visual-quality audit", ["cmd", "/c", "scripts\\run_figure_visual_quality_audit.cmd"]),
        Step("manual figure review sheet", ["cmd", "/c", "scripts\\run_manual_figure_review_sheet.cmd"]),
        Step("strict figure/source-data integrity audit", ["cmd", "/c", "scripts\\run_figure_data_integrity_audit.cmd", "--strict"]),
        Step("strict manuscript submission text audit", ["cmd", "/c", "scripts\\run_manuscript_submission_text_audit.cmd", "--strict"]),
        Step("reference metadata audit", ["cmd", "/c", "scripts\\run_reference_metadata_audit.cmd"]),
        Step("journal submission metadata audit", ["cmd", "/c", "scripts\\run_journal_submission_metadata_audit.cmd"]),
        Step("publication package validation", ["cmd", "/c", "scripts\\validate_publication_package.cmd"]),
        Step("repository deposit readiness audit", ["cmd", "/c", "scripts\\run_repository_deposit_readiness_audit.cmd"]),
        Step("submission artifact consistency audit", ["cmd", "/c", "scripts\\run_submission_artifact_consistency_audit.cmd"]),
        Step("final QC acceptance audit", ["cmd", "/c", "scripts\\run_final_qc_acceptance_audit.cmd"]),
        Step("publication readiness summary", ["cmd", "/c", "scripts\\run_publication_readiness_summary.cmd"]),
    ]

    for step in steps:
        run_step(step, report)
        if not step.passed:
            break

    if all(step.passed for step in report.steps) and len(report.steps) == len(steps):
        check_final_artifacts(report)

    if report.passed:
        write_reports(report)
        run_step(Step("archive handoff audit", ["cmd", "/c", "scripts\\run_archive_handoff_audit.cmd"]), report)
        if report.passed:
            run_step(Step("publication readiness summary (final)", ["cmd", "/c", "scripts\\run_publication_readiness_summary.cmd"]), report)
        if report.passed:
            write_reports(report)
            run_step(Step("final evidence index", ["cmd", "/c", "scripts\\run_final_evidence_index.cmd"]), report)

    write_reports(report)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())

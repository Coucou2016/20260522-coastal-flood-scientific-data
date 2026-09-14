from __future__ import annotations

import json
import py_compile
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "publication_gate_scripts_audit.txt"
REPORT_JSON = LOG_DIR / "publication_gate_scripts_audit.json"

REQUIRED_SCRIPTS = [
    ROOT / "scripts" / "finalize_cee_publication_package.py",
    ROOT / "scripts" / "audit_publication_readiness.py",
    ROOT / "scripts" / "audit_python_runtime_dependencies.py",
    ROOT / "scripts" / "validate_publication_package.py",
    ROOT / "scripts" / "publication_gate.py",
    ROOT / "scripts" / "build_manuscript_figure_inventory.py",
    ROOT / "scripts" / "audit_figure_deliverables.py",
    ROOT / "scripts" / "audit_figure_visual_quality.py",
    ROOT / "scripts" / "build_manual_figure_review_sheet.py",
    ROOT / "scripts" / "audit_figure_data_integrity.py",
    ROOT / "scripts" / "audit_manuscript_submission_text.py",
    ROOT / "scripts" / "audit_reference_metadata.py",
    ROOT / "scripts" / "audit_journal_submission_metadata.py",
    ROOT / "scripts" / "audit_submission_artifact_consistency.py",
    ROOT / "scripts" / "audit_final_qc_acceptance.py",
    ROOT / "scripts" / "audit_repository_deposit_readiness.py",
    ROOT / "scripts" / "audit_archive_handoff.py",
    ROOT / "scripts" / "build_publication_readiness_summary.py",
    ROOT / "scripts" / "build_final_evidence_index.py",
]

REQUIRED_ENTRYPOINTS = [
    ROOT / "scripts" / "run_python_checked.cmd",
    ROOT / "scripts" / "diagnose_publication_environment.cmd",
    ROOT / "scripts" / "install_publication_requirements.cmd",
    ROOT / "scripts" / "run_publication_audit.cmd",
    ROOT / "scripts" / "run_python_runtime_dependencies_audit.cmd",
    ROOT / "scripts" / "run_finalization.cmd",
    ROOT / "scripts" / "validate_publication_package.cmd",
    ROOT / "scripts" / "run_publication_gate.cmd",
    ROOT / "scripts" / "run_manuscript_figure_inventory.cmd",
    ROOT / "scripts" / "run_figure_deliverables_audit.cmd",
    ROOT / "scripts" / "run_figure_visual_quality_audit.cmd",
    ROOT / "scripts" / "run_manual_figure_review_sheet.cmd",
    ROOT / "scripts" / "run_figure_data_integrity_audit.cmd",
    ROOT / "scripts" / "run_manuscript_submission_text_audit.cmd",
    ROOT / "scripts" / "run_reference_metadata_audit.cmd",
    ROOT / "scripts" / "run_journal_submission_metadata_audit.cmd",
    ROOT / "scripts" / "run_submission_artifact_consistency_audit.cmd",
    ROOT / "scripts" / "run_final_qc_acceptance_audit.cmd",
    ROOT / "scripts" / "run_repository_deposit_readiness_audit.cmd",
    ROOT / "scripts" / "run_archive_handoff_audit.cmd",
    ROOT / "scripts" / "run_publication_readiness_summary.cmd",
    ROOT / "scripts" / "run_final_evidence_index.cmd",
    ROOT / "scripts" / "run_all_publication_checks.cmd",
]

ENTRYPOINT_EXPECTATIONS = {
    ROOT / "scripts" / "run_python_checked.cmd": ["where python", "python %*"],
    ROOT / "scripts" / "diagnose_publication_environment.cmd": [
        "logs\\publication_environment_diagnostics.txt",
        "Diagnostic-only log",
        "Passed: True",
    ],
    ROOT / "scripts" / "install_publication_requirements.cmd": [
        "call scripts\\run_python_checked.cmd -m pip install -r requirements-publication.txt",
    ],
    ROOT / "scripts" / "run_publication_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_publication_readiness.py"],
    ROOT / "scripts" / "run_python_runtime_dependencies_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_python_runtime_dependencies.py"],
    ROOT / "scripts" / "run_finalization.cmd": ["call scripts\\run_python_checked.cmd scripts\\finalize_cee_publication_package.py"],
    ROOT / "scripts" / "validate_publication_package.cmd": ["call scripts\\run_python_checked.cmd scripts\\validate_publication_package.py"],
    ROOT / "scripts" / "run_publication_gate.cmd": [
        "call scripts\\diagnose_publication_environment.cmd",
        "call scripts\\run_python_checked.cmd scripts\\publication_gate.py",
    ],
    ROOT / "scripts" / "run_manuscript_figure_inventory.cmd": ["call scripts\\run_python_checked.cmd scripts\\build_manuscript_figure_inventory.py"],
    ROOT / "scripts" / "run_figure_deliverables_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_figure_deliverables.py"],
    ROOT / "scripts" / "run_figure_visual_quality_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_figure_visual_quality.py"],
    ROOT / "scripts" / "run_manual_figure_review_sheet.cmd": ["call scripts\\run_python_checked.cmd scripts\\build_manual_figure_review_sheet.py"],
    ROOT / "scripts" / "run_figure_data_integrity_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_figure_data_integrity.py"],
    ROOT / "scripts" / "run_manuscript_submission_text_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_manuscript_submission_text.py"],
    ROOT / "scripts" / "run_reference_metadata_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_reference_metadata.py"],
    ROOT / "scripts" / "run_journal_submission_metadata_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_journal_submission_metadata.py"],
    ROOT / "scripts" / "run_submission_artifact_consistency_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_submission_artifact_consistency.py"],
    ROOT / "scripts" / "run_final_qc_acceptance_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_final_qc_acceptance.py"],
    ROOT / "scripts" / "run_repository_deposit_readiness_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_repository_deposit_readiness.py"],
    ROOT / "scripts" / "run_archive_handoff_audit.cmd": ["call scripts\\run_python_checked.cmd scripts\\audit_archive_handoff.py"],
    ROOT / "scripts" / "run_publication_readiness_summary.cmd": ["call scripts\\run_python_checked.cmd scripts\\build_publication_readiness_summary.py"],
    ROOT / "scripts" / "run_final_evidence_index.cmd": ["call scripts\\run_python_checked.cmd scripts\\build_final_evidence_index.py"],
    ROOT / "scripts" / "run_all_publication_checks.cmd": ["call scripts\\run_final_submission_handoff.cmd"],
}


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def normalize_command_text(text: str) -> str:
    return " ".join(text.lower().replace("/", "\\").split())


def check_python_scripts(audit: Audit) -> None:
    for path in REQUIRED_SCRIPTS:
        audit.checked.append(rel(path))
        if not path.exists():
            audit.errors.append(f"Missing required Python script: {rel(path)}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            audit.errors.append(f"Python syntax check failed for {rel(path)}: {exc.msg}")


def check_entrypoints(audit: Audit) -> None:
    for path in REQUIRED_ENTRYPOINTS:
        audit.checked.append(rel(path))
        if not path.exists():
            audit.errors.append(f"Missing required command entrypoint: {rel(path)}")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            audit.errors.append(f"Cannot read command entrypoint {rel(path)}: {exc}")
            continue
        if "python " not in text.lower() and "call " not in text.lower():
            audit.warnings.append(f"Command entrypoint may not invoke any validation step: {rel(path)}")
        if "exit /b" not in text.lower():
            audit.warnings.append(f"Command entrypoint does not explicitly propagate exit code: {rel(path)}")
        normalized = normalize_command_text(text)
        for expected in ENTRYPOINT_EXPECTATIONS.get(path, []):
            if normalize_command_text(expected) not in normalized:
                audit.errors.append(f"Command entrypoint {rel(path)} does not invoke expected target: {expected}")
        if path.name == "run_all_publication_checks.cmd" and "%*" not in text:
            audit.errors.append(f"Command wrapper {rel(path)} must forward arguments with %*.")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "checked": audit.checked,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Publication Gate Scripts Audit",
        "==============================",
        "",
        f"Passed: {audit.passed}",
        f"Checked: {len(audit.checked)}",
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
    check_python_scripts(audit)
    check_entrypoints(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())

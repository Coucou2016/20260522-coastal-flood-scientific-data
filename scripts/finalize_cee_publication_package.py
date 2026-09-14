from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
MANUSCRIPT_DIR = ROOT / "manuscript"
FIG_DIR = ROOT / "figures" / "main"
SOURCE_DIR = ROOT / "data" / "figure_source"
PACKAGE_DIR = ROOT / "publication_package"
PACKAGE_ZIP = ROOT / "publication_package.zip"
FAILED_STATUS = ROOT / "publication_package_failed_status.json"
FAILED_LOG = LOG_DIR / "cee_publication_finalize_failed.md"


COMMANDS = [
    ("verify raw downloads", [sys.executable, "scripts/verify_downloads.py", "--strict"]),
    ("quality audit", [sys.executable, "scripts/combo1_quality_audit.py"]),
    ("rebuild refined figures", [sys.executable, "scripts/make_cee_refined_figures.py"]),
    ("rebuild review HTML", [sys.executable, "scripts/build_cee_review_html.py"]),
    ("compile key scripts", [sys.executable, "-m", "py_compile", "scripts/make_cee_refined_figures.py", "scripts/build_cee_review_html.py", "scripts/audit_publication_readiness.py", "scripts/validate_publication_package.py", "scripts/finalize_cee_publication_package.py"]),
    ("publication readiness audit", [sys.executable, "scripts/audit_publication_readiness.py"]),
]


MAIN_FIGURES = [
    "Fig1_process_terrain_design.png",
    "Fig2_water_level_divergence.png",
    "Fig3_meteorological_coherence.png",
    "Fig4_deltadtm_terrain_sensitivity.png",
    "Fig5_process_terrain_typology.png",
]

MAIN_FIGURE_PDFS = [name.replace(".png", ".pdf") for name in MAIN_FIGURES]


SOURCE_TABLES = [
    "Fig1_station_metadata.csv",
    "Fig2_water_level_divergence.csv",
    "Fig3_driver_correlations.csv",
    "Fig4_connected_terrain_sensitivity.csv",
    "Fig4_hypsometry_curves.csv",
    "Fig5_process_terrain_typology.csv",
    "Table1_data_products.csv",
    "Table2_water_level_indicators.csv",
    "Table3_driver_correlations.csv",
    "Table4_deltadtm_connected_sensitivity.csv",
]

MANUSCRIPT_FILES = [
    "process_terrain_coastal_flood_CEE_manuscript.md",
    "process_terrain_coastal_flood_CEE_manuscript_review.html",
    "process_terrain_CEE_figure_work_plan.md",
    "publication_readiness_audit.md",
    "reference_verification.md",
    "figure_source_data_dictionary.md",
    "figure_final_qc_protocol.md",
    "reviewer_risk_register.md",
    "claims_evidence_matrix.md",
    "submission_metadata_required.md",
    "submission_package_matrix.md",
    "cover_letter_draft.md",
    "editorial_significance_statement.md",
    "author_final_confirmation_form.md",
    "title_page_and_declarations_draft.md",
    "publication_release_notes_template.md",
    "target_journal_cee_checklist.md",
    "nature_reporting_summary_preparation.md",
    "ai_use_statement_draft.md",
    "data_code_availability_final_draft.md",
    "data_repository_deposit_checklist.md",
    "repository_readme_template.md",
    "citation_metadata_template.md",
    "license_decision_notes.md",
    "supplementary_information_draft.md",
    "review_response_preparation.md",
    "software_environment.md",
    "process_terrain_CEE_finalization_checklist.md",
    "final_submission_index.md",
    "external_finalization_guide.md",
]

KEY_SCRIPTS = [
    "scripts/make_cee_refined_figures.py",
    "scripts/build_cee_review_html.py",
    "scripts/audit_publication_readiness.py",
    "scripts/validate_publication_package.py",
    "scripts/finalize_cee_publication_package.py",
    "scripts/run_finalization.cmd",
    "scripts/run_publication_audit.cmd",
    "scripts/verify_downloads.py",
    "scripts/combo1_quality_audit.py",
    "scripts/validate_publication_package.cmd",
]

ROOT_PACKAGE_FILES = [
    "requirements.txt",
    "environment.yml",
    "config/combo1_stations.yaml",
    "NEXT_ACTIONS.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_step(name: str, cmd: list[str], log_lines: list[str]) -> None:
    log_lines.append(f"\n## {name}\n")
    log_lines.append("Command: `" + " ".join(cmd) + "`\n")
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.stdout:
        log_lines.append("\n```text\n" + proc.stdout.strip() + "\n```\n")
    if proc.stderr:
        log_lines.append("\n```text\n" + proc.stderr.strip() + "\n```\n")
    log_lines.append(f"Exit code: `{proc.returncode}`\n")
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}")


def reset_finalization_outputs() -> None:
    """Remove stale finalization outputs before any verification step runs."""
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    if FAILED_STATUS.exists():
        FAILED_STATUS.unlink()
    if FAILED_LOG.exists():
        FAILED_LOG.unlink()


def artifact_manifest() -> dict:
    artifacts: dict[str, list[dict[str, object]]] = {"figures": [], "source_tables": [], "manuscript": [], "environment": []}
    for name in MAIN_FIGURES + MAIN_FIGURE_PDFS:
        path = FIG_DIR / name
        artifacts["figures"].append(
            {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None, "sha256": sha256(path) if path.exists() else None}
        )
    for name in SOURCE_TABLES:
        path = SOURCE_DIR / name
        artifacts["source_tables"].append(
            {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None, "sha256": sha256(path) if path.exists() else None}
        )
    for name in MANUSCRIPT_FILES:
        path = MANUSCRIPT_DIR / name
        artifacts["manuscript"].append(
            {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None, "sha256": sha256(path) if path.exists() else None}
        )
    for rel in ROOT_PACKAGE_FILES:
        path = ROOT / rel
        artifacts["environment"].append(
            {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None, "sha256": sha256(path) if path.exists() else None}
        )
    return artifacts


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_publication_package(report: Path) -> None:
    (PACKAGE_DIR / "figures" / "main").mkdir(parents=True, exist_ok=True)
    (PACKAGE_DIR / "data" / "figure_source").mkdir(parents=True, exist_ok=True)
    (PACKAGE_DIR / "manuscript").mkdir(parents=True, exist_ok=True)
    (PACKAGE_DIR / "scripts").mkdir(parents=True, exist_ok=True)

    for name in MANUSCRIPT_FILES:
        copy_if_exists(MANUSCRIPT_DIR / name, PACKAGE_DIR / "manuscript" / name)
    copy_if_exists(report, PACKAGE_DIR / "manuscript" / report.name)
    for name in MAIN_FIGURES + MAIN_FIGURE_PDFS:
        copy_if_exists(FIG_DIR / name, PACKAGE_DIR / "figures" / "main" / name)
    for name in SOURCE_TABLES:
        copy_if_exists(SOURCE_DIR / name, PACKAGE_DIR / "data" / "figure_source" / name)
    for rel in KEY_SCRIPTS:
        copy_if_exists(ROOT / rel, PACKAGE_DIR / rel)
    for rel in ROOT_PACKAGE_FILES:
        copy_if_exists(ROOT / rel, PACKAGE_DIR / rel)
    readme = PACKAGE_DIR / "README.md"
    readme.write_text(
        "# Process-terrain coastal flood manuscript package\n\n"
        "This directory contains the local manuscript review package generated by "
        "`scripts/finalize_cee_publication_package.py`.\n\n"
        "## Contents\n\n"
        "- `manuscript/final_submission_index.md`: human-facing entry point for the package.\n"
        "- `completion_status.json`: machine-readable finalization status and remaining manual items.\n"
        "- `manuscript/`: manuscript Markdown, standalone review HTML, audit notes and finalization report.\n"
        "- `figures/main/`: main figures as PNG and PDF.\n"
        "- `data/figure_source/`: source CSV tables used to draw the figures and manuscript tables.\n"
        "- `scripts/`: key scripts required to rebuild and audit the package.\n\n"
        "The package may include `logs/prearchive_publication_package_validation.txt`, which records the validation run performed before that log was copied into the package. "
        "For a fresh validation of the final archive, run `python scripts/validate_publication_package.py` or `scripts\\validate_publication_package.cmd` from the project root.\n\n"
        "Raw GSSR, COAST-RP, Open-Meteo and DeltaDTM files are not duplicated here because they are public upstream data products and can be large. "
        "Their provenance and required checks are documented in the manuscript and audit files.\n\n"
        "## Acceptance condition\n\n"
        "Treat this package as current only if `manuscript/publication_readiness_report.md` exists and records a successful finalization run. "
        "If the finalization workflow failed, inspect `logs/cee_publication_finalize_failed.md` and `publication_package_failed_status.json` in the project root.\n",
        encoding="utf-8",
    )
    write_completion_status(report, state="pending_verification")
    manifest_path = PACKAGE_DIR / "package_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = package_manifest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verify_publication_package(manifest)
    write_completion_status(report, state="finalized")
    manifest = package_manifest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verify_publication_package(manifest)
    build_package_zip()
    verify_package_zip({item["path"] for item in manifest["files"]})
    write_final_archive_manifest()
    validate_final_archive_with_log()
    validate_publication_package_with_log()
    copy_if_exists(LOG_DIR / "publication_package_validation.txt", PACKAGE_DIR / "logs" / "prearchive_publication_package_validation.txt")
    manifest = package_manifest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verify_publication_package(manifest)
    build_package_zip()
    verify_package_zip({item["path"] for item in manifest["files"]})
    write_final_archive_manifest()
    validate_final_archive_with_log()


def validate_publication_package_with_log() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/validate_publication_package.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    validation_log = LOG_DIR / "publication_package_validation.txt"
    validation_log.write_text(
        "Command: python scripts/validate_publication_package.py\n\n"
        f"Exit code: {proc.returncode}\n\n"
        "STDOUT:\n"
        f"{proc.stdout}\n\n"
        "STDERR:\n"
        f"{proc.stderr}\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"publication package validation failed; see {validation_log}")


def validate_final_archive_with_log() -> None:
    """Validate the final archive without modifying the package contents."""
    proc = subprocess.run(
        [sys.executable, "scripts/validate_publication_package.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    validation_log = LOG_DIR / "final_archive_validation.txt"
    validation_log.write_text(
        "Command: python scripts/validate_publication_package.py\n\n"
        f"Exit code: {proc.returncode}\n\n"
        "STDOUT:\n"
        f"{proc.stdout}\n\n"
        "STDERR:\n"
        f"{proc.stderr}\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"final archive validation failed; see {validation_log}")


def write_final_archive_manifest() -> None:
    archive_bytes = PACKAGE_ZIP.stat().st_size if PACKAGE_ZIP.exists() else None
    archive_sha256 = sha256(PACKAGE_ZIP) if PACKAGE_ZIP.exists() else None
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive": str(PACKAGE_ZIP.relative_to(ROOT)).replace("\\", "/"),
        "bytes": archive_bytes,
        "sha256": archive_sha256,
        "publication_package_zip": {
            "path": str(PACKAGE_ZIP.relative_to(ROOT)).replace("\\", "/"),
            "bytes": archive_bytes,
            "sha256": archive_sha256,
        },
        "package_dir": str(PACKAGE_DIR.relative_to(ROOT)).replace("\\", "/"),
        "validation_log": "logs/final_archive_validation.txt",
    }
    (ROOT / "final_archive_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_completion_status(report: Path, state: str) -> None:
    status = {
        "status": state,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "finalization_report": str(report.relative_to(ROOT)).replace("\\", "/"),
        "standalone_html": "manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html",
        "package_dir": "publication_package",
        "package_zip": "publication_package.zip",
        "audit_expected": "PUBLICATION READINESS AUDIT: PASS",
        "manual_completion_required": [
            "author list and affiliations",
            "author contributions",
            "funding statement",
            "competing interests statement",
            "processed-data repository DOI",
            "code/package repository DOI",
            "target-journal submission metadata",
            "final author sign-off",
        ],
        "do_not_treat_as_final_if": [
            "publication_readiness_report.md is missing",
            "publication_readiness_report.md does not record PUBLICATION READINESS AUDIT: PASS",
            "publication_package.zip is missing",
            "author_final_confirmation_form.md is incomplete",
        ],
    }
    status_text = json.dumps(status, indent=2) + "\n"
    (PACKAGE_DIR / "completion_status.json").write_text(status_text, encoding="utf-8")
    (ROOT / "completion_status.json").write_text(status_text, encoding="utf-8")


def write_failure_status(exc: Exception, failure_log: Path) -> None:
    status = {
        "status": "failed",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "error": str(exc),
        "failure_log": str(failure_log.relative_to(ROOT)).replace("\\", "/"),
        "publication_package_exists": PACKAGE_DIR.exists(),
        "publication_package_zip_exists": PACKAGE_ZIP.exists(),
        "safe_to_use_existing_package": False,
        "next_step": "Resolve the failure log, then rerun scripts/finalize_cee_publication_package.py.",
    }
    FAILED_STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")


def package_manifest() -> dict:
    files = []
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(PACKAGE_DIR)).replace("\\", "/")
            files.append(
                {
                    "path": rel,
                    "bytes": None if rel == "package_manifest.json" else path.stat().st_size,
                    "sha256": None if rel == "package_manifest.json" else sha256(path),
                    "note": "self-referential manifest; size and hash intentionally omitted" if rel == "package_manifest.json" else "",
                }
            )
    return {
        "package_root": str(PACKAGE_DIR),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "scripts/finalize_cee_publication_package.py",
        "file_count": len(files),
        "files": files,
    }


def verify_publication_package(manifest: dict) -> None:
    present = {item["path"] for item in manifest["files"]}
    required = required_package_members()
    missing = sorted(required - present)
    if missing:
        raise RuntimeError("publication_package is missing required files: " + ", ".join(missing))


def required_package_members() -> set[str]:
    required = {"README.md", "package_manifest.json"}
    required.add("completion_status.json")
    required.update(f"manuscript/{name}" for name in MANUSCRIPT_FILES)
    required.update(f"figures/main/{name}" for name in MAIN_FIGURES + MAIN_FIGURE_PDFS)
    required.update(f"data/figure_source/{name}" for name in SOURCE_TABLES)
    required.update(rel.replace("\\", "/") for rel in KEY_SCRIPTS)
    required.update(rel.replace("\\", "/") for rel in ROOT_PACKAGE_FILES)
    required.add("manuscript/publication_readiness_report.md")
    return required


def build_package_zip() -> None:
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(PACKAGE_DIR.parent))


def verify_package_zip(manifest_members: set[str] | None = None) -> None:
    if not PACKAGE_ZIP.exists() or PACKAGE_ZIP.stat().st_size < 100_000:
        raise RuntimeError(f"publication archive missing or suspiciously small: {PACKAGE_ZIP}")
    with zipfile.ZipFile(PACKAGE_ZIP, "r") as zf:
        names = set(zf.namelist())
    required_members = manifest_members if manifest_members is not None else required_package_members()
    required = {f"publication_package/{name}" for name in required_members}
    missing = sorted(required - names)
    if missing:
        raise RuntimeError("publication archive is missing required files: " + ", ".join(missing))


def write_report(log_lines: list[str], manifest: dict) -> Path:
    report = MANUSCRIPT_DIR / "publication_readiness_report.md"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Publication readiness report\n",
        f"Generated: `{now}`\n",
        "\n## Summary\n",
        "The finalization workflow rebuilt the main figures and standalone manuscript review HTML, then ran raw-data, algorithm and figure-source consistency checks.\n",
        "\n## Artifact manifest\n",
        "```json\n" + json.dumps(manifest, indent=2) + "\n```\n",
        "\n## Command log\n",
        *log_lines,
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    log_lines: list[str] = []
    try:
        reset_finalization_outputs()
        for name, cmd in COMMANDS:
            run_step(name, cmd, log_lines)
        manifest = artifact_manifest()
        report = write_report(log_lines, manifest)
        build_publication_package(report)
    except Exception as exc:  # noqa: BLE001 - finalization should produce a readable failure log.
        failure = FAILED_LOG
        failure.write_text("\n".join(log_lines + [f"\n# Failure\n\n{exc}\n"]), encoding="utf-8")
        write_failure_status(exc, failure)
        print(f"FINALIZATION FAILED: {exc}")
        print(f"Failure log: {failure}")
        return 1
    print("CEE publication package finalized.")
    print(f"Report: {report}")
    print(f"Package: {PACKAGE_DIR}")
    print(f"Archive: {PACKAGE_ZIP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

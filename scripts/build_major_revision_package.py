#!/usr/bin/env python3
"""Build a credential-scanned reviewer package from an explicit allowlist."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "major_revision_reviewer_package.zip"
CONTENT_MANIFEST = ROOT / "major_revision_package_content_manifest.json"
RECEIPT = ROOT / "major_revision_package_receipt.json"

ROOT_FILES = [
    "README.md",
    "CHANGELOG.md",
    "DATA_AVAILABILITY.md",
    "LICENSE",
    "pyproject.toml",
    "requirements-publication.txt",
    "requirements-lock.txt",
    "environment.yml",
    "environment-lock.yml",
    "reproduction_receipt.json",
    "data/derived_input_manifest.json",
    "config/submission_links.json",
    "data/upstream_raw_manifest.csv",
    "data/upstream_raw_manifest.json",
    "paper.html",
    "paper.md",
    "paper.pdf",
    "supplementary_information.html",
    "supplementary_information.md",
    "supplementary_information.pdf",
    "report.html",
    "report.md",
    "report.pdf",
]

MANUSCRIPT_FILES = [
    "manuscript/process_terrain_coastal_flood_CEE_manuscript.md",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.html",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.md",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.pdf",
    "manuscript/process_terrain_coastal_flood_CEE_supplementary.html",
    "manuscript/process_terrain_coastal_flood_CEE_supplementary.md",
    "manuscript/process_terrain_coastal_flood_CEE_supplementary.pdf",
    "manuscript/scientific_integrity_review.html",
    "manuscript/scientific_integrity_review.md",
    "manuscript/scientific_integrity_review.pdf",
    "manuscript/internal_scientific_consistency_audit.html",
    "manuscript/internal_scientific_consistency_audit.md",
    "manuscript/internal_scientific_consistency_audit.pdf",
    "manuscript/external_review_resolution.md",
    "manuscript/reproduction_environment_followup_20260926.md",
]

FIGURE_FILES = [
    f"figures/main/{stem}.{extension}"
    for stem in [
        "Fig1_process_terrain_design",
        "Fig2_regional_screening_agreement",
        "Fig3_connected_terrain_contrasts",
        "Fig4_metric_decomposition_robustness",
        "FigS1_water_level_definition",
        "FigS2_process_coherence",
        "FigS3_connectivity_gallery",
        "FigS4_elevation_product_datum_sensitivity",
        "FigS5_coastrp_match_audit",
    ]
    for extension in ["png", "pdf"]
]

SOURCE_TABLES = [
    "data/figure_source/Primary_sample_flow.csv",
    "data/figure_source/Primary_station_spatial_blocks.csv",
    "data/figure_source/Primary_terrain_components_68stations.csv",
    "data/figure_source/DeltaDTM_v1_1_product_version_audit.csv",
    "data/figure_source/Terrain_robustness_grid_74stations.csv",
    "data/figure_source/Rank_robustness_one_at_a_time.csv",
    "data/figure_source/Spatial_block_bootstrap_intervals.csv",
    "data/figure_source/Leave_one_coastal_sector_out.csv",
    "data/figure_source/Topk_spatial_null_curves.csv",
    "data/figure_source/Return_period_sensitivity.csv",
    "data/figure_source/Station_influence_jackknife.csv",
    "data/figure_source/Basin_specific_associations.csv",
    "data/figure_source/Spatial_autocorrelation_moran.csv",
    "data/figure_source/Denominator_geometry_68stations.csv",
    "data/figure_source/Denominator_adjusted_associations.csv",
    "data/figure_source/Topology_membership_changes.csv",
    "data/figure_source/Topology_sensitivity_summary.csv",
    "data/figure_source/Match_distance_audit_74stations.csv",
    "data/figure_source/Match_distance_histogram_source.csv",
    "data/figure_source/Tidal_covariation_diagnostics.csv",
    "data/figure_source/FigS1_tidal_source_audit.csv",
    "data/figure_source/GSSR_metadata_field_audit.csv",
    "data/figure_source/External_review_method_audit.json",
    "data/figure_source/Fig3_predefined_site_selection.csv",
    "data/figure_source/Fig3_threshold_response_source.csv",
    "data/figure_source/TableS_local_dtm_product_datum_crosscheck.csv",
    "data/figure_source/Fig2_water_level_divergence_with_uncertainty.csv",
    "data/figure_source/TableS_tidal_regime_metadata_source_tracked.csv",
    "data/figure_source/Fig3_driver_correlations.csv",
]

CODE_SUFFIXES = {".py", ".cmd", ".ps1"}


def repository_code_files() -> list[str]:
    files: list[str] = []
    for directory in ("src", "scripts", "tests"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and path.suffix.lower() in CODE_SUFFIXES:
                files.append(path.relative_to(ROOT).as_posix())
    files.extend(
        [
            "config/coastal_spatial_blocks_v2.csv",
            "config/combo1_stations.yaml",
        ]
    )
    return files

PATTERNS = {
    "OpenAI-style key": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "local bridge unlock code": re.compile(rb"LOCALBRIDGE_OAUTH_UNLOCK_CODE\s*="),
    "ngrok authtoken": re.compile(rb"(?i:ngrok.{0,40}authtoken\s*[:=])"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "unavailable: no committed Git baseline"


def main() -> None:
    all_source_tables = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "data" / "figure_source").glob("*"))
        if path.is_file()
    ]
    relative_paths = list(
        dict.fromkeys(
            ROOT_FILES
            + MANUSCRIPT_FILES
            + FIGURE_FILES
            + SOURCE_TABLES
            + all_source_tables
            + repository_code_files()
        )
    )
    if any(Path(path).name.startswith(".env") for path in relative_paths):
        raise SystemExit("Refusing to package an environment file")

    missing = [path for path in relative_paths if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("Missing allowlisted files: " + ", ".join(missing))

    findings: list[str] = []
    entries: list[dict[str, object]] = []
    for relative in relative_paths:
        path = ROOT / relative
        content = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{label}: {relative}")
        entries.append({"path": relative, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    if findings:
        raise SystemExit("Credential scan failed:\n" + "\n".join(findings))

    manifest = {
        "schema": "coastal-flood-major-revision-package-content-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": f"Git commit {current_git_commit()}; archived derived reproduction is pinned by reproduction_receipt.json and per-file SHA-256",
        "security_scan": "PASS: no configured credential pattern detected in allowlisted files",
        "exclusions": [
            ".git and VCS metadata",
            ".env files, credentials, cookies and browser state",
            "raw upstream rasters/archives and provider downloads",
            "node_modules, caches, temporary renderings and logs",
            "historical publication packages and obsolete figure workflows",
        ],
        "files": entries,
    }
    CONTENT_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in relative_paths:
            archive.write(ROOT / relative, arcname=f"major_revision/{relative}")
        archive.write(CONTENT_MANIFEST, arcname="major_revision/major_revision_package_content_manifest.json")

    receipt = {
        "package": ZIP_PATH.name,
        "bytes": ZIP_PATH.stat().st_size,
        "sha256": sha256(ZIP_PATH),
        "content_manifest": CONTENT_MANIFEST.name,
        "content_manifest_sha256": sha256(CONTENT_MANIFEST),
        "credential_scan": "PASS",
        "git_commit": current_git_commit(),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a credential-scanned reviewer package from an explicit allowlist."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "major_revision_reviewer_package.zip"
CONTENT_MANIFEST = ROOT / "major_revision_package_content_manifest.json"
RECEIPT = ROOT / "major_revision_package_receipt.json"

ROOT_FILES = [
    "README.md",
    "requirements-publication.txt",
    "major_revision_manifest.json",
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
    "manuscript/external_review_resolution.md",
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
    "data/figure_source/Primary_station_coastal_sectors.csv",
    "data/figure_source/Primary_terrain_components_68stations.csv",
    "data/figure_source/DeltaDTM_v1_1_product_version_audit.csv",
    "data/figure_source/Terrain_robustness_grid_74stations.csv",
    "data/figure_source/Rank_robustness_one_at_a_time.csv",
    "data/figure_source/Spatial_sector_bootstrap_intervals.csv",
    "data/figure_source/Leave_one_coastal_sector_out.csv",
    "data/figure_source/Topk_spatial_null_curves.csv",
    "data/figure_source/Return_period_sensitivity.csv",
    "data/figure_source/Station_influence_jackknife.csv",
    "data/figure_source/Sector_specific_associations.csv",
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

SCRIPT_FILES = [
    "scripts/add_mask_aware_terrain_diagnostics.py",
    "scripts/rebuild_frozen_primary_analysis.py",
    "scripts/add_external_review_diagnostics.py",
    "scripts/add_local_dtm_validation.py",
    "scripts/make_major_revision_figures.py",
    "scripts/build_standalone_paper.py",
    "scripts/build_supplementary_information.py",
    "scripts/build_research_report_v2.py",
    "scripts/build_scientific_integrity_review_v2.py",
    "scripts/validate_standalone_html.py",
    "scripts/run_major_revision_rebuild.py",
    "scripts/run_major_revision_rebuild.cmd",
    "scripts/build_major_revision_package.py",
    "tests/test_scientific_contracts.py",
]

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


def main() -> None:
    relative_paths = ROOT_FILES + MANUSCRIPT_FILES + FIGURE_FILES + SOURCE_TABLES + SCRIPT_FILES
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
        "baseline": "local workspace is not a Git repository; baseline is major_revision_manifest.json",
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
        "git_commit": "not applicable: workspace is not a Git repository",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

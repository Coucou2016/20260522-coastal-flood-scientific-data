#!/usr/bin/env python3
"""Rebuild and verify the frozen major-revision manuscript package."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "major_revision_rebuild.log"
MANIFEST = ROOT / "major_revision_manifest.json"

STEPS = [
    ("frozen 68-station analysis", [sys.executable, "scripts/rebuild_frozen_primary_analysis.py"]),
    ("external-review spatial and topology diagnostics", [sys.executable, "scripts/add_external_review_diagnostics.py"]),
    ("local-DTM product/datum cross-check", [sys.executable, "scripts/add_local_dtm_validation.py"]),
    ("SciencePlots figures", [sys.executable, "scripts/make_major_revision_figures.py"]),
    ("standalone manuscript", [sys.executable, "scripts/build_standalone_paper.py"]),
    ("supplementary information", [sys.executable, "scripts/build_supplementary_information.py"]),
    ("research report", [sys.executable, "scripts/build_research_report_v2.py"]),
    ("scientific-integrity review", [sys.executable, "scripts/build_scientific_integrity_review_v2.py"]),
    (
        "standalone HTML validation",
        [
            sys.executable,
            "scripts/validate_standalone_html.py",
            "paper.html",
            "supplementary_information.html",
            "report.html",
            "manuscript/scientific_integrity_review.html",
        ],
    ),
    (
        "scientific contracts",
        [sys.executable, "-m", "pytest", "tests", "-q", "--import-mode=importlib"],
    ),
]

OUTPUTS = [
    "paper.html",
    "paper.md",
    "paper.pdf",
    "supplementary_information.html",
    "supplementary_information.md",
    "supplementary_information.pdf",
    "report.html",
    "report.md",
    "report.pdf",
    "manuscript/scientific_integrity_review.html",
    "manuscript/scientific_integrity_review.md",
    "manuscript/scientific_integrity_review.pdf",
    "manuscript/external_review_resolution.md",
    "data/figure_source/Primary_terrain_components_68stations.csv",
    "data/figure_source/Terrain_robustness_grid_74stations.csv",
    "data/figure_source/Rank_robustness_one_at_a_time.csv",
    "data/figure_source/Spatial_sector_bootstrap_intervals.csv",
    "data/figure_source/Topk_spatial_null_curves.csv",
    "data/figure_source/Return_period_sensitivity.csv",
    "data/figure_source/Denominator_adjusted_associations.csv",
    "data/figure_source/Topology_sensitivity_summary.csv",
    "data/figure_source/Match_distance_audit_74stations.csv",
    "data/figure_source/TableS_local_dtm_product_datum_crosscheck.csv",
    "data/figure_source/TableS_tidal_regime_metadata_source_tracked.csv",
    "figures/main/Fig1_process_terrain_design.pdf",
    "figures/main/Fig2_regional_screening_agreement.pdf",
    "figures/main/Fig3_connected_terrain_contrasts.pdf",
    "figures/main/Fig4_metric_decomposition_robustness.pdf",
    "figures/main/FigS4_elevation_product_datum_sensitivity.pdf",
    "figures/main/FigS5_coastrp_match_audit.pdf",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    records: list[dict[str, object]] = []
    log_parts: list[str] = []

    for name, command in STEPS:
        print(f"[major-revision] {name}", flush=True)
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        output = completed.stdout or ""
        print(output, end="")
        log_parts.append(f"## {name}\nCommand: {' '.join(command)}\nExit: {completed.returncode}\n\n{output}\n")
        records.append({"name": name, "command": command, "exit_code": completed.returncode})
        if completed.returncode:
            LOG.write_text("\n".join(log_parts), encoding="utf-8")
            raise SystemExit(completed.returncode)

    artifacts: list[dict[str, object]] = []
    missing: list[str] = []
    for relative in OUTPUTS:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(relative)
            continue
        artifacts.append(
            {
                "path": relative.replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if missing:
        raise SystemExit("Missing or empty outputs: " + ", ".join(missing))

    payload = {
        "schema": "coastal-flood-major-revision-manifest-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "steps": records,
        "artifacts": artifacts,
        "manual_items_remaining": [
            "authors, affiliations, funding and contributions",
            "repository DOI or private reviewer link",
            "common vertical-datum harmonization for national/local DTM comparisons",
            "independent dynamic or observed hazard benchmark",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.write_text("\n".join(log_parts), encoding="utf-8")
    print(f"Wrote {MANIFEST}")
    print(f"Wrote {LOG}")


if __name__ == "__main__":
    run()

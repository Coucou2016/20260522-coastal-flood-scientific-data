#!/usr/bin/env python3
"""Run the full upstream publication gate and isolated reviewer-package check."""

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
    ("full raw-to-paper reproduction", [sys.executable, "scripts/reproduce.py", "--mode", "full"]),
    ("freeze compact derived inputs", [sys.executable, "scripts/build_derived_input_manifest.py"]),
]

POST_MANIFEST_STEPS = [
    ("build credential-scanned reviewer archive", [sys.executable, "scripts/build_major_revision_package.py"]),
    ("validate reviewer archive in isolation", [sys.executable, "scripts/validate_reviewer_archive.py"]),
]

OUTPUTS = [
    "paper.html", "paper.md", "paper.pdf",
    "supplementary_information.html", "supplementary_information.md", "supplementary_information.pdf",
    "report.html", "report.md", "report.pdf",
    "manuscript/process_terrain_coastal_flood_CEE_manuscript.md",
    "manuscript/internal_scientific_consistency_audit.html",
    "manuscript/internal_scientific_consistency_audit.md",
    "manuscript/internal_scientific_consistency_audit.pdf",
    "figures/main/Fig1_process_terrain_design.png",
    "figures/main/Fig2_regional_screening_agreement.png",
    "figures/main/Fig3_connected_terrain_contrasts.png",
    "figures/main/Fig4_metric_decomposition_robustness.png",
    "data/figure_source/Primary_terrain_components_68stations.csv",
    "data/figure_source/Return_period_sensitivity.csv",
    "data/figure_source/Spatial_block_bootstrap_intervals.csv",
    "data/figure_source/Topk_spatial_null_curves.csv",
    "data/figure_source/Water_land_topology_sensitivity_68stations.csv",
    "data/figure_source/Threshold_response_0_3m_68stations.csv",
    "data/figure_source/Coastline_oriented_window_68stations.csv",
    "data/figure_source/Decision_instability_station_metrics.csv",
    "data/figure_source/COAST_RP_same_coast_match_audit.csv",
    "data/derived_input_manifest.json",
    "reproduction_receipt.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_step(name: str, command: list[str], env: dict[str, str]) -> tuple[dict[str, object], str]:
    print(f"[publication-gate] {name}", flush=True)
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
    record = {"name": name, "command": command, "exit_code": completed.returncode}
    if completed.returncode:
        raise RuntimeError(f"Step failed ({completed.returncode}): {name}\n{output}")
    return record, f"## {name}\nCommand: {' '.join(command)}\nExit: {completed.returncode}\n\n{output}\n"


def artifact_records(extra: list[str] | None = None) -> list[dict[str, object]]:
    paths = OUTPUTS + (extra or [])
    missing = [relative for relative in paths if not (ROOT / relative).is_file() or (ROOT / relative).stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing or empty outputs: " + ", ".join(missing))
    return [
        {"path": relative, "bytes": (ROOT / relative).stat().st_size, "sha256": sha256(ROOT / relative)}
        for relative in paths
    ]


def write_manifest(records: list[dict[str, object]], artifacts: list[dict[str, object]], stage: str) -> None:
    payload = {
        "schema": "coastal-flood-major-revision-manifest-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "python": sys.version,
        "reproduction_scope": "full upstream raw-to-paper workflow followed by isolated derived-input reviewer reproduction",
        "steps": records,
        "artifacts": artifacts,
        "manual_items_remaining": [
            "authors, affiliations, funding and contributions",
            "formal archival DOI",
            "common vertical-datum harmonization for national/local DTM comparisons",
            "independent dynamic or observed flood-hazard benchmark",
            "coastline-component and alongshore-distance validation for COAST-RP matching",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    records: list[dict[str, object]] = []
    log_parts: list[str] = []
    try:
        for name, command in STEPS:
            record, log = run_step(name, command, env)
            records.append(record)
            log_parts.append(log)
        write_manifest(records, artifact_records(), "analysis-complete-before-reviewer-archive")
        for name, command in POST_MANIFEST_STEPS:
            record, log = run_step(name, command, env)
            records.append(record)
            log_parts.append(log)
        extra = [
            "major_revision_reviewer_package.zip",
            "major_revision_package_content_manifest.json",
            "major_revision_package_receipt.json",
        ]
        write_manifest(records, artifact_records(extra), "publication-gate-complete")
    except Exception as exc:
        log_parts.append(f"## FAILURE\n{type(exc).__name__}: {exc}\n")
        LOG.write_text("\n".join(log_parts), encoding="utf-8")
        raise
    LOG.write_text("\n".join(log_parts), encoding="utf-8")
    print(f"Wrote {MANIFEST}")
    print(f"Wrote {LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

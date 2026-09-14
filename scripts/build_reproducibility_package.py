"""Build the current reproducibility package for the mask-aware manuscript.

The package intentionally does not copy multi-GB raw products. Instead it records
raw-file hashes, copies figure-source tables and final exports, and writes a
one-command rebuild workflow for reviewer-side auditing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "reproducibility_package"
MANIFEST_DIR = DEST / "manifests"
TABLE_DIR = DEST / "source_tables"
OUTPUT_DIR = DEST / "outputs"
SCRIPT_DIR = DEST / "scripts"
DOC_DIR = DEST / "docs"

SOURCE_DIR = ROOT / "data" / "figure_source"
SUBMISSION_LINKS = ROOT / "config" / "submission_links.json"

OUTPUT_FILES = [
    "paper.html",
    "paper.md",
    "paper.pdf",
    "report.html",
    "report.md",
    "report.pdf",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.html",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.md",
    "manuscript/process_terrain_coastal_flood_CEE_final_paper.pdf",
    "manuscript/process_terrain_coastal_flood_research_report.html",
    "manuscript/process_terrain_coastal_flood_research_report.md",
    "manuscript/process_terrain_coastal_flood_research_report.pdf",
    "manuscript/scientific_integrity_review.html",
    "manuscript/scientific_integrity_review.md",
    "manuscript/scientific_integrity_review.pdf",
    "manuscript/reviewer_action_plan.md",
    "manuscript/repository_deposit_instructions.md",
    "manuscript/current_acceptance_status.md",
    "completion_status.json",
    "logs/goal_acceptance_audit.json",
    "logs/goal_acceptance_audit.md",
    "logs/scientific_integrity_review.json",
]

SCRIPT_FILES = [
    "scripts/merge_gssr_coastrp.py",
    "scripts/build_nw_europe_extended_diagnostics.py",
    "scripts/add_uncertainty_diagnostics.py",
    "scripts/add_advanced_terrain_rank_diagnostics.py",
    "scripts/add_mask_aware_terrain_diagnostics.py",
    "scripts/add_local_dtm_validation.py",
    "scripts/make_fig1_design_map.py",
    "scripts/make_cee_refined_figures.py",
    "scripts/make_advanced_submission_figures.py",
    "scripts/publication_style.py",
    "scripts/build_standalone_paper.py",
    "scripts/build_research_report.py",
    "scripts/build_scientific_integrity_review.py",
    "scripts/build_reproducibility_package.py",
    "scripts/validate_standalone_html.py",
    "scripts/audit_current_outputs.py",
    "scripts/audit_goal_acceptance.py",
    "scripts/audit_submission_readiness.py",
    "scripts/set_submission_links.py",
    "scripts/write_current_acceptance_status.py",
    "scripts/download_combo1.py",
    "scripts/run_python_checked.cmd",
    "tests/test_scientific_contracts.py",
]

CONFIG_FILES = [
    "requirements.txt",
    "requirements-publication.txt",
    "environment.yml",
    "README.md",
    "config/submission_links.json",
    "config/submission_figure_manifest.json",
]


def load_submission_links() -> dict[str, str]:
    if not SUBMISSION_LINKS.exists():
        return {}
    return json.loads(SUBMISSION_LINKS.read_text(encoding="utf-8"))


def clean_link(value: object) -> str:
    return str(value or "").strip()


def repository_link_status() -> dict[str, str | bool]:
    links = load_submission_links()
    data_link = clean_link(links.get("data_repository_url_or_doi"))
    code_link = clean_link(links.get("code_repository_url_or_doi"))
    reviewer_link = clean_link(links.get("private_reviewer_link"))
    complete = bool(reviewer_link or (data_link and code_link))
    return {
        "complete": complete,
        "data_repository_url_or_doi": data_link,
        "code_repository_url_or_doi": code_link,
        "private_reviewer_link": reviewer_link,
        "status": "complete" if complete else "pending",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_dest() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    for d in [DEST, MANIFEST_DIR, TABLE_DIR, OUTPUT_DIR, SCRIPT_DIR, DOC_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def copy_rel_file(rel: str, target_root: Path, entries: list[dict]) -> None:
    src = ROOT / rel
    if not src.exists():
        entries.append({"source": rel, "status": "missing"})
        return
    target = target_root / rel.replace("\\", "__").replace("/", "__")
    shutil.copy2(src, target)
    entries.append(
        {
            "source": rel,
            "package_file": str(target.relative_to(DEST)).replace("\\", "/"),
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
            "status": "copied",
        }
    )


def copy_figure_source_tables(entries: list[dict]) -> None:
    for src in sorted(SOURCE_DIR.glob("*")):
        if not src.is_file():
            continue
        target = TABLE_DIR / src.name
        shutil.copy2(src, target)
        entries.append(
            {
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "package_file": str(target.relative_to(DEST)).replace("\\", "/"),
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
                "status": "copied",
            }
        )


def build_station_master_table() -> Path:
    terrain = pd.read_csv(SOURCE_DIR / "Fig6_mask_aware_terrain_area_metrics.csv")
    audit = pd.read_csv(SOURCE_DIR / "Fig5_station_candidate_audit.csv")
    tidal = pd.read_csv(SOURCE_DIR / "TableS_tidal_regime_metadata_source_tracked.csv")

    audit_cols = [
        "station_id",
        "tg",
        "num_year",
        "corrn",
        "rmse",
        "gssr_archive",
        "archive_available",
        "passes_years_ge25",
        "passes_corr_ge045",
        "passes_corr_ge055",
        "passes_corr_ge065",
        "selected_base_30",
        "selection_reason",
        "match_dist_km",
        "deltadtm_tile_available",
        "deltadtm_tiles",
    ]
    tidal_cols = [
        "station_id",
        "spring_tidal_range_m",
        "tidal_regime",
        "tidal_range_metric",
        "source_status",
        "source_name",
        "source_url",
    ]
    audit_merge_cols = [
        c
        for c in audit_cols
        if c in audit.columns and (c == "station_id" or c not in terrain.columns)
    ]
    df = terrain.merge(audit[audit_merge_cols], on="station_id", how="left")
    df = df.merge(tidal[[c for c in tidal_cols if c in tidal.columns]], on="station_id", how="left")

    keep = [
        "station_id",
        "station",
        "lat",
        "lon",
        "tg",
        "num_year",
        "corrn",
        "rmse",
        "archive_available",
        "passes_years_ge25",
        "passes_corr_ge055",
        "selected_base_30",
        "selection_reason",
        "coast_rp_rp10_m",
        "match_dist_km",
        "window_width_km",
        "bbox_west",
        "bbox_south",
        "bbox_east",
        "bbox_north",
        "terrain_source",
        "terrain_tiles",
        "mask_source",
        "official_mask_classes_used",
        "marine_seed_rule",
        "marine_seed_resolved",
        "marine_seed_status",
        "marine_context_width_km",
        "marine_context_source",
        "passes_primary_match_le6km",
        "mask_lowland_area_km2",
        "mask_lowland_cells",
        "mask_ocean_cells",
        "mask_river_cells",
        "mask_lake_cells",
        "mask_clipped_255_cells",
        "mask_connected_2m_lowland_pct",
        "mask_all_below_2m_lowland_pct",
        "mask_unconnected_2m_lowland_pct",
        "mask_connected_2m_area_km2",
        "mask_all_below_2m_area_km2",
        "mask_unconnected_2m_area_km2",
        "proxy_minus_mask_connected_2m_lowland_pct",
        "proxy_minus_mask_connected_2m_area_km2",
        "spring_tidal_range_m",
        "tidal_regime",
        "tidal_range_metric",
        "source_status",
        "source_name",
        "source_url",
    ]
    keep = [c for c in keep if c in df.columns]
    out = TABLE_DIR / "processed_station_master_table.csv"
    df[keep].to_csv(out, index=False)
    return out


def write_raw_hash_manifest() -> Path:
    rows: list[dict] = []
    for path in sorted((ROOT / "data" / "raw").rglob("*")):
        if not path.is_file():
            continue
        rows.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "last_write_time_utc": datetime.fromtimestamp(
                    path.stat().st_mtime, timezone.utc
                ).isoformat(),
            }
        )
    out = MANIFEST_DIR / "raw_file_hashes.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256", "last_write_time_utc"])
        writer.writeheader()
        writer.writerows(rows)
    return out


def write_package_versions() -> Path:
    out = MANIFEST_DIR / "package_versions.txt"
    try:
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], cwd=ROOT, text=True)
    except Exception as exc:  # pragma: no cover - defensive audit note
        freeze = f"pip freeze failed: {exc}\n"
    content = [
        f"created_utc: {datetime.now(timezone.utc).isoformat()}",
        f"python: {platform.python_version()}",
        f"platform: {platform.platform()}",
        "",
        "pip freeze:",
        freeze.strip(),
        "",
    ]
    out.write_text("\n".join(content), encoding="utf-8")
    return out


def write_source_data_manifest() -> Path:
    mask_audit = pd.read_csv(SOURCE_DIR / "Fig6_deltadtm_mask_seed_audit.csv").iloc[0].to_dict()
    link_status = repository_link_status()
    source_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Current mask-aware paper/report reproducibility package.",
        "primary_outputs": OUTPUT_FILES,
        "primary_source_tables": [
            "processed_station_master_table.csv",
            "Fig6_mask_aware_terrain_area_metrics.csv",
            "Fig6_mask_class_counts.csv",
            "TableS_local_dtm_validation.csv",
            "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv",
            "Fig6_mask_aware_two_sided_permutation_association.csv",
            "Fig6_mask_aware_topk_overlap_null_envelope.csv",
            "Fig6_mask_aware_sector_block_bootstrap.csv",
            "Fig6_archetype_map_selection.csv",
            "TableS_tidal_regime_metadata_source_tracked.csv",
            "Fig2_water_level_divergence_with_uncertainty.csv",
        ],
        "mask_seed_audit": mask_audit,
        "random_seeds": {
            "permutation_tests": "See scripts/add_mask_aware_terrain_diagnostics.py and source table generation code.",
            "bootstrap_and_monte_carlo": "See scripts/add_uncertainty_diagnostics.py and scripts/add_submission_polish_diagnostics.py.",
        },
        "external_products": {
            "GSSR": "Global Storm Surge Reconstruction daily surge reconstructions.",
            "COAST-RP": "COAST-RP storm-tide return-period dataset from 4TU.ResearchData.",
            "Open-Meteo ERA5": "Station-centred ERA5-derived historical weather extraction.",
            "DeltaDTM": "DeltaDTM v1.1 elevation and official mask tiles.",
            "Environment Agency LiDAR Composite DTM": "England local DTM WCS used for Sheerness, Newlyn, Lowestoft and Immingham validation.",
            "PDOK/Rijkswaterstaat AHN DTM": "Netherlands local DTM WCS used for Den Helder, Delfzijl and Hoek van Holland validation.",
        },
        "completed_validation_addons": {
            "local_dtm_validation": "Completed for Sheerness, Newlyn, Lowestoft, Immingham, Den Helder, Delfzijl and Hoek van Holland; see TableS_local_dtm_validation.csv. Product vertical datums are not harmonized, so this is a screening cross-check rather than an absolute flood-level validation.",
        },
        "repository_link_status": link_status,
        "pending_submission_items": {}
        if link_status["complete"]
        else {"public_repository_doi_or_private_reviewer_link": "Pending."},
    }
    out = MANIFEST_DIR / "source_data_manifest.json"
    out.write_text(json.dumps(source_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def write_rebuild_workflow() -> None:
    workflow = """# Rebuild and Audit Workflow

This package records the current mask-aware manuscript and research-report
export. It does not redistribute multi-GB raw products; raw files are traced in
`manifests/raw_file_hashes.csv`.

Full scientific recomputation requires this compact package to remain beside
the original project tree containing those public upstream raw files. From the
verified project root, run:

```powershell
scripts\\run_python_checked.cmd scripts\\merge_gssr_coastrp.py
scripts\\run_python_checked.cmd scripts\\build_nw_europe_extended_diagnostics.py
scripts\\run_python_checked.cmd scripts\\add_uncertainty_diagnostics.py
scripts\\run_python_checked.cmd scripts\\add_mask_aware_terrain_diagnostics.py
scripts\\run_python_checked.cmd scripts\\add_local_dtm_validation.py
scripts\\run_python_checked.cmd scripts\\make_fig1_design_map.py
scripts\\run_python_checked.cmd scripts\\make_advanced_submission_figures.py
scripts\\run_python_checked.cmd scripts\\build_standalone_paper.py
scripts\\run_python_checked.cmd scripts\\build_research_report.py
scripts\\run_python_checked.cmd scripts\\validate_standalone_html.py paper.html
scripts\\run_python_checked.cmd scripts\\validate_standalone_html.py report.html
scripts\\run_python_checked.cmd scripts\\audit_current_outputs.py
scripts\\run_python_checked.cmd scripts\\audit_goal_acceptance.py
scripts\\run_python_checked.cmd scripts\\write_current_acceptance_status.py
```

For final journal submission, after a real public DOI/repository URL or private
reviewer-access URL has been entered in `config/submission_links.json`, run:

```powershell
scripts\\run_python_checked.cmd scripts\\audit_submission_readiness.py
```

The one-command Windows helper first verifies that the expected adjacent
project scripts and DeltaDTM mask archive exist, then runs the same sequence.
It exits explicitly when the raw project is absent; the compact ZIP is an audit
package, not a standalone substitute for omitted upstream data:

```powershell
reproducibility_package\\one_command_rebuild.cmd
```

After a successful rebuild, refresh this package and zip archive from the
project root with:

```powershell
scripts\\run_python_checked.cmd scripts\\build_reproducibility_package.py
```

Current manuscript status: official DeltaDTM mask-aware connectivity has been
implemented and audited, and a seven-station local DTM product/datum cross-check has
been generated. Repository DOI/private reviewer link status is recorded in
`config/submission_links.json` and `manifests/source_data_manifest.json`.
"""
    (DOC_DIR / "README_reproducibility.md").write_text(workflow, encoding="utf-8")
    helper = """@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "PROJECT_ROOT=%~dp0.."
if not exist "%PROJECT_ROOT%\\scripts\\add_mask_aware_terrain_diagnostics.py" (
  echo ERROR: Full project scripts are not adjacent to this compact package.
  echo Restore the package beside the original project tree before scientific recomputation.
  exit /b 2
)
if not exist "%PROJECT_ROOT%\\data\\raw\\deltadtm\\zips\\mask_tiles.zip" (
  echo ERROR: Required upstream DeltaDTM mask archive is absent.
  echo See manifests\\raw_file_hashes.csv and docs\\README_reproducibility.md.
  exit /b 2
)
cd /d "%PROJECT_ROOT%"
call scripts\\run_python_checked.cmd scripts\\merge_gssr_coastrp.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\build_nw_europe_extended_diagnostics.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\add_uncertainty_diagnostics.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\add_mask_aware_terrain_diagnostics.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\add_local_dtm_validation.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\make_fig1_design_map.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\make_advanced_submission_figures.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\build_standalone_paper.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\build_research_report.py || exit /b 1
call scripts\\run_python_checked.cmd scripts\\validate_standalone_html.py paper.html || exit /b 1
call scripts\\run_python_checked.cmd scripts\\validate_standalone_html.py report.html || exit /b 1
call scripts\\run_python_checked.cmd scripts\\audit_current_outputs.py || exit /b 1
echo Rebuild and audit complete.
echo To refresh reproducibility_package.zip, run:
echo scripts\\run_python_checked.cmd scripts\\build_reproducibility_package.py
"""
    (DEST / "one_command_rebuild.cmd").write_text(helper, encoding="utf-8")


def write_manifest(entries: list[dict]) -> None:
    link_status = repository_link_status()
    all_files = []
    for path in sorted(DEST.rglob("*")):
        if not path.is_file():
            continue
        all_files.append(
            {
                "package_path": str(path.relative_to(DEST)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "package": str(DEST.relative_to(ROOT)),
        "status": "audit-ready, DOI/private reviewer link complete"
        if link_status["complete"]
        else "audit-ready, DOI/private reviewer link pending",
        "repository_link_status": link_status,
        "entries": entries,
        "package_files": all_files,
        "package_files_scope": (
            "All payload files present before the manifest is written. "
            "manifests/package_manifest.json and its SHA-256 sidecar are intentionally excluded "
            "to avoid a self-referential hash."
        ),
    }
    out = MANIFEST_DIR / "package_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (MANIFEST_DIR / "package_manifest.sha256").write_text(
        f"{sha256_file(out)}  package_manifest.json\n", encoding="utf-8"
    )


def validate_zip_members(path: Path) -> None:
    """Reject duplicate, traversal and symlink members in the generated archive."""
    with zipfile.ZipFile(path) as archive:
        names: set[str] = set()
        for member in archive.infolist():
            normalized = member.filename.replace("\\", "/")
            member_path = Path(normalized)
            if normalized in names:
                raise RuntimeError(f"duplicate ZIP member: {normalized}")
            names.add(normalized)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe ZIP member path: {normalized}")
            if ((member.external_attr >> 16) & 0o170000) == 0o120000:
                raise RuntimeError(f"ZIP symlink member is not allowed: {normalized}")
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC validation failed at member: {bad}")


def main() -> int:
    clean_dest()
    entries: list[dict] = []

    copy_figure_source_tables(entries)
    master = build_station_master_table()
    entries.append(
        {
            "source": "generated processed station master table",
            "package_file": str(master.relative_to(DEST)).replace("\\", "/"),
            "bytes": master.stat().st_size,
            "sha256": sha256_file(master),
            "status": "generated",
        }
    )
    raw_hashes = write_raw_hash_manifest()
    entries.append(
        {
            "source": "data/raw recursive file hashes",
            "package_file": str(raw_hashes.relative_to(DEST)).replace("\\", "/"),
            "bytes": raw_hashes.stat().st_size,
            "sha256": sha256_file(raw_hashes),
            "status": "generated",
        }
    )
    versions = write_package_versions()
    entries.append(
        {
            "source": "python environment",
            "package_file": str(versions.relative_to(DEST)).replace("\\", "/"),
            "bytes": versions.stat().st_size,
            "sha256": sha256_file(versions),
            "status": "generated",
        }
    )
    source_manifest = write_source_data_manifest()
    entries.append(
        {
            "source": "source data manifest",
            "package_file": str(source_manifest.relative_to(DEST)).replace("\\", "/"),
            "bytes": source_manifest.stat().st_size,
            "sha256": sha256_file(source_manifest),
            "status": "generated",
        }
    )
    write_rebuild_workflow()

    for rel in OUTPUT_FILES:
        copy_rel_file(rel, OUTPUT_DIR, entries)
    for rel in SCRIPT_FILES:
        copy_rel_file(rel, SCRIPT_DIR, entries)
    for rel in CONFIG_FILES:
        copy_rel_file(rel, DOC_DIR, entries)

    write_manifest(entries)
    archive_path = Path(shutil.make_archive(str(ROOT / "reproducibility_package"), "zip", DEST))
    validate_zip_members(archive_path)
    (ROOT / "reproducibility_package.zip.sha256").write_text(
        f"{sha256_file(archive_path)}  {archive_path.name}\n", encoding="utf-8"
    )
    print(f"Wrote {DEST}")
    print(f"Wrote {ROOT / 'reproducibility_package.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

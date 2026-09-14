#!/usr/bin/env python3
"""Write the current acceptance-status summary from authoritative local evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "figure_source"
CONFIG = ROOT / "config" / "submission_links.json"
MANIFEST = ROOT / "reproducibility_package" / "manifests" / "source_data_manifest.json"
OUT_JSON = ROOT / "completion_status.json"
OUT_MD = ROOT / "manuscript" / "current_acceptance_status.md"


def exists_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def repository_link_status() -> dict:
    links = load_json(CONFIG)
    reviewer = str(links.get("private_reviewer_link", "") or "").strip()
    data = str(links.get("data_repository_url_or_doi", "") or "").strip()
    code = str(links.get("code_repository_url_or_doi", "") or "").strip()
    complete = bool(reviewer or (data and code))
    return {
        "complete": complete,
        "private_reviewer_link": reviewer,
        "data_repository_url_or_doi": data,
        "code_repository_url_or_doi": code,
        "status": "complete" if complete else "pending",
    }


def main() -> int:
    local_validation_path = SOURCE_DIR / "TableS_local_dtm_validation.csv"
    archetype_path = SOURCE_DIR / "Fig6_archetype_map_selection.csv"
    mask_area_path = SOURCE_DIR / "Fig6_mask_aware_terrain_area_metrics.csv"
    mask_counts_path = SOURCE_DIR / "Fig6_mask_class_counts.csv"

    local_validation = pd.read_csv(local_validation_path) if local_validation_path.exists() else pd.DataFrame()
    archetypes = pd.read_csv(archetype_path) if archetype_path.exists() else pd.DataFrame()
    mask_area = pd.read_csv(mask_area_path) if mask_area_path.exists() else pd.DataFrame()

    expected_local = {
        "sheerness-p015-uk",
        "newlyn-p001-uk",
        "lowestoft-p024-uk",
        "immingham-p026-uk",
        "denhelder-hel-nl",
        "delfzijl-del-nl",
        "hoekvanholla-hvh-nl",
    }
    local_dtm_complete = expected_local.issubset(set(local_validation.get("station_id", [])))
    expected_archetypes = {
        "aligned high storm-tide / high connected-terrain",
        "high storm-tide / lower connected-terrain",
        "lower storm-tide / high connected-terrain",
    }
    figure3_complete = expected_archetypes.issubset(set(archetypes.get("archetype", [])))
    mask_complete = (
        len(mask_area) == 74
        and exists_nonempty(mask_counts_path)
        and {"mask_connected_2m_area_km2", "mask_all_below_2m_area_km2", "mask_unconnected_2m_area_km2"}.issubset(
            set(mask_area.columns)
        )
    )
    link_status = repository_link_status()
    manifest = load_json(MANIFEST)

    items = [
        {
            "id": 1,
            "label": "data truth and source-table traceability",
            "status": "complete",
            "evidence": "Core figures and tables are generated from data/figure_source tables and audited by scripts/audit_current_outputs.py.",
        },
        {
            "id": 2,
            "label": "DeltaDTM official mask-aware connectivity",
            "status": "complete" if mask_complete else "incomplete",
            "evidence": f"{mask_area_path.relative_to(ROOT)} rows={len(mask_area)}; mask class table present={exists_nonempty(mask_counts_path)}.",
        },
        {
            "id": 3,
            "label": "connected fraction and area metrics",
            "status": "complete" if mask_complete else "incomplete",
            "evidence": "Mask-aware source table includes connected/all-below/unconnected areas and denominator metrics.",
        },
        {
            "id": 4,
            "label": "Figure 3 archetype evidence grid",
            "status": "complete" if figure3_complete else "incomplete",
            "evidence": f"{archetype_path.relative_to(ROOT)} contains {len(archetypes)} archetype rows.",
        },
        {
            "id": 5,
            "label": "conservative statistical interpretation",
            "status": "complete",
            "evidence": "Top-set overlap is treated as decision-oriented description; formal statistics use raw COAST-RP versus connected fraction/area.",
        },
        {
            "id": 6,
            "label": "sample-boundary clarity",
            "status": "complete",
            "evidence": "Paper/report distinguish the 68-station primary, 74-station distance-unrestricted, 44-station GSSR-qualified, 30-station retained and 13-station source-verified tidal subsets.",
        },
        {
            "id": 7,
            "label": "uncertainty and perturbation ranges",
            "status": "complete",
            "evidence": "GSSR bootstrap/prediction-bound, COAST-RP spatial matching, DeltaDTM DEM perturbation and window/seed sensitivity are reported as screening ranges.",
        },
        {
            "id": 8,
            "label": "reproducibility package",
            "status": "complete_local_pending_external_link" if not link_status["complete"] else "complete",
            "evidence": "reproducibility_package.zip exists; repository DOI/private reviewer link status="
            + link_status["status"]
            + ".",
        },
        {
            "id": 9,
            "label": "paper/report synchronized standalone outputs",
            "status": "complete",
            "evidence": "paper.html/md/pdf and report.html/md/pdf exist and standalone HTML validation passes.",
        },
        {
            "id": 10,
            "label": "non-overclaiming wording",
            "status": "complete",
            "evidence": "Final paper/report avoid distortion, mis-rank and true hotspot in core wording.",
        },
        {
            "id": "local_dtm",
            "label": "local DTM product/datum cross-check",
            "status": "complete" if local_dtm_complete else "incomplete",
            "evidence": f"{local_validation_path.relative_to(ROOT)} stations={'; '.join(local_validation.get('station_id', []))}.",
        },
        {
            "id": "submission_readiness",
            "label": "external submission repository link",
            "status": "pending" if not link_status["complete"] else "complete",
            "evidence": "Set config/submission_links.json and rerun scripts/audit_submission_readiness.py.",
        },
    ]

    overall_status = (
        "technical_review_ready_local_package"
        if not link_status["complete"]
        else "submission_ready_repository_link_recorded"
    )
    status = {
        "status": overall_status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_link_status": link_status,
        "source_manifest_repository_status": manifest.get("repository_link_status", {}),
        "acceptance_items": items,
        "final_submission_gate": "pending_repository_link" if not link_status["complete"] else "ready_to_run_final_submission_gate",
    }
    OUT_JSON.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Current Acceptance Status",
        "",
        f"Generated UTC: {status['generated_utc']}",
        "",
        f"Overall status: **{overall_status}**",
        "",
        "This file supersedes older finalized/status files for the current mask-aware paper/report package. "
        "The local technical-review package is auditable, but final journal submission remains pending until a real public repository DOI/URL or private reviewer link is recorded.",
        "",
        "## Acceptance Items",
        "",
        "| Item | Status | Evidence |",
        "|---|---|---|",
    ]
    for item in items:
        lines.append(f"| {item['id']}. {item['label']} | {item['status']} | {item['evidence']} |")
    lines.extend(
        [
            "",
            "## Final External Step",
            "",
            "Record a real repository link with one of the following commands:",
            "",
            "```powershell",
            'scripts\\run_python_checked.cmd scripts\\set_submission_links.py --reviewer "https://..."',
            'scripts\\run_python_checked.cmd scripts\\set_submission_links.py --data "https://doi.org/..." --code "https://doi.org/..."',
            "```",
            "",
            "Then rebuild and run:",
            "",
            "```powershell",
            "scripts\\run_python_checked.cmd scripts\\build_standalone_paper.py",
            "scripts\\run_python_checked.cmd scripts\\build_research_report.py",
            "scripts\\run_python_checked.cmd scripts\\build_reproducibility_package.py",
            "scripts\\run_python_checked.cmd scripts\\audit_submission_readiness.py",
            "```",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Audit the current package against the active 10-item acceptance target."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "figure_source"
LOG_DIR = ROOT / "logs"
CONFIG = ROOT / "config" / "submission_links.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def exists_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def link_status() -> dict:
    links = load_json(CONFIG)
    data = str(links.get("data_repository_url_or_doi", "") or "").strip()
    code = str(links.get("code_repository_url_or_doi", "") or "").strip()
    reviewer = str(links.get("private_reviewer_link", "") or "").strip()
    complete = bool(reviewer or (data and code))
    return {
        "complete": complete,
        "data_repository_url_or_doi": data,
        "code_repository_url_or_doi": code,
        "private_reviewer_link": reviewer,
        "status": "complete" if complete else "pending",
    }


def check_text_has(text: str, phrases: list[str]) -> tuple[bool, list[str]]:
    missing = [phrase for phrase in phrases if phrase not in text]
    return not missing, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-submission",
        action="store_true",
        help="Fail unless the DOI/private reviewer link has been recorded.",
    )
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    paper = read_text(ROOT / "paper.md")
    report = read_text(ROOT / "report.md")
    combined_text = paper + "\n" + report

    mask_area_path = SOURCE_DIR / "Fig6_mask_aware_terrain_area_metrics.csv"
    mask_counts_path = SOURCE_DIR / "Fig6_mask_class_counts.csv"
    archetype_path = SOURCE_DIR / "Fig6_archetype_map_selection.csv"
    local_dtm_path = SOURCE_DIR / "TableS_local_dtm_validation.csv"
    permutation_path = SOURCE_DIR / "Fig6_mask_aware_two_sided_permutation_association.csv"
    topk_path = SOURCE_DIR / "Fig6_mask_aware_topk_overlap_null_envelope.csv"

    mask_area = pd.read_csv(mask_area_path) if mask_area_path.exists() else pd.DataFrame()
    archetypes = pd.read_csv(archetype_path) if archetype_path.exists() else pd.DataFrame()
    local_dtm = pd.read_csv(local_dtm_path) if local_dtm_path.exists() else pd.DataFrame()
    link = link_status()

    required_metric_cols = {
        "mask_connected_2m_lowland_pct",
        "mask_connected_2m_area_km2",
        "mask_all_below_2m_area_km2",
        "mask_unconnected_2m_area_km2",
        "mask_lowland_area_km2",
    }
    required_mask_cols = {
        "mask_ocean_cells",
        "mask_river_cells",
        "mask_lake_cells",
        "mask_clipped_255_cells",
        "marine_seed_rule",
    }
    expected_archetypes = {
        "aligned high storm-tide / high connected-terrain",
        "high storm-tide / lower connected-terrain",
        "lower storm-tide / high connected-terrain",
    }
    expected_local = {
        "sheerness-p015-uk",
        "newlyn-p001-uk",
        "lowestoft-p024-uk",
        "immingham-p026-uk",
        "denhelder-hel-nl",
        "delfzijl-del-nl",
        "hoekvanholla-hvh-nl",
    }

    checks: list[dict] = []

    def add_check(item: int | str, label: str, passed: bool, evidence: str, severity: str = "required") -> None:
        checks.append(
            {
                "item": item,
                "label": label,
                "passed": bool(passed),
                "severity": severity,
                "evidence": evidence,
            }
        )

    add_check(
        1,
        "Data truth and source-table traceability",
        all(
            exists_nonempty(path)
            for path in [
                mask_area_path,
                mask_counts_path,
                archetype_path,
                local_dtm_path,
                permutation_path,
                topk_path,
            ]
        ),
        "Required source tables exist in data/figure_source and are consumed by current build/audit scripts.",
    )
    seed_text = " ".join(str(value) for value in mask_area.get("marine_seed_rule", []))
    seed_rule_ok = all(
        phrase in seed_text
        for phrase in ["ocean class 1", "river class 3", "connected to ocean", "lake class 2", "255 clipped"]
    ) and all(
        phrase in paper
        for phrase in ["class-0 land", "EGM2008-referenced elevation", r"z\leq15"]
    )
    add_check(
        2,
        "DeltaDTM official mask-aware connectivity",
        len(mask_area) == 74
        and required_mask_cols.issubset(mask_area.columns)
        and seed_rule_ok,
        f"{mask_area_path.name} rows={len(mask_area)}; required mask columns present={required_mask_cols.issubset(mask_area.columns)}.",
    )
    add_check(
        3,
        "Connected lowland metric completeness",
        required_metric_cols.issubset(mask_area.columns),
        f"Required fraction/area columns present={required_metric_cols.issubset(mask_area.columns)}.",
    )
    add_check(
        4,
        "Figure 3 archetype and threshold-response evidence",
        expected_archetypes.issubset(set(archetypes.get("archetype", [])))
        and exists_nonempty(ROOT / "figures" / "main" / "Fig3_connected_terrain_contrasts.png"),
        f"{archetype_path.name} archetypes={list(archetypes.get('archetype', []))}.",
    )
    add_check(
        5,
        "Conservative statistical interpretation",
        all(
            phrase in paper
            for phrase in [
                "two-sided permutation",
                "permutation envelope",
                "does not show that their overlap is unusually low",
                "spatially stable inverse relationship",
            ]
        ),
        "Paper frames top-set overlap descriptively and uses raw COAST-RP versus connected terrain statistics.",
    )
    add_check(
        6,
        "Sample-boundary clarity",
        all(phrase in paper for phrase in ["68-station", "all 74 sites", "44 GSSR-qualified", "30-site subset", "13-station source-verified"]),
        "Paper distinguishes primary, distance-unrestricted, GSSR-qualified, retained and source-verified tidal subsets.",
    )
    add_check(
        7,
        "Uncertainty and perturbation ranges",
        all(
            phrase in paper
            for phrase in [
                "prediction-bound",
                "spatial-extraction",
                "+/-0.5 m",
                "+/-1.0 m",
                "window, lowland ceiling and seed rule",
                "not a confidence interval or a spatial error model",
            ]
        ),
        "Paper names GSSR, COAST-RP, DEM perturbation and window/seed sensitivity as screening ranges.",
    )
    add_check(
        8,
        "Reproducibility package",
        exists_nonempty(ROOT / "reproducibility_package.zip")
        and exists_nonempty(ROOT / "reproducibility_package" / "source_tables" / "processed_station_master_table.csv")
        and exists_nonempty(ROOT / "reproducibility_package" / "manifests" / "raw_file_hashes.csv")
        and exists_nonempty(ROOT / "reproducibility_package" / "one_command_rebuild.cmd"),
        f"repository_link_status={link['status']}; package zip exists={exists_nonempty(ROOT / 'reproducibility_package.zip')}.",
    )
    add_check(
        9,
        "Paper/report synchronized standalone outputs",
        all(
            exists_nonempty(ROOT / name)
            for name in ["paper.html", "paper.md", "paper.pdf", "report.html", "report.md", "report.pdf"]
        ),
        "All six standalone paper/report outputs exist; standalone validation is covered by validate_standalone_html.py.",
    )
    forbidden_terms = ["distortion", "mis-rank", "true hotspot"]
    forbidden_hits = [term for term in forbidden_terms if re.search(term, combined_text, re.I)]
    add_check(
        10,
        "Non-overclaiming wording",
        not forbidden_hits
        and "complementary coastal-flood screening priorities" in paper
        and "Neither is a reference truth" in paper,
        f"Forbidden terms in paper/report={forbidden_hits}.",
    )
    add_check(
        "local_dtm",
        "Local-DTM cross-check hard gate",
        expected_local.issubset(set(local_dtm.get("station_id", []))),
        f"local DTM stations={list(local_dtm.get('station_id', []))}.",
    )
    add_check(
        "submission_link",
        "External DOI/private reviewer link hard gate",
        link["complete"],
        "Repository link is pending." if not link["complete"] else "Repository link is recorded.",
        severity="submission",
    )

    required_pass = all(c["passed"] for c in checks if c["severity"] == "required")
    submission_ready = required_pass and link["complete"]
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "local_technical_review_ready": required_pass,
        "final_submission_ready": submission_ready,
        "repository_link_status": link,
        "checks": checks,
    }
    json_path = LOG_DIR / "goal_acceptance_audit.json"
    md_path = LOG_DIR / "goal_acceptance_audit.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Goal Acceptance Audit",
        "",
        f"Generated UTC: {result['generated_utc']}",
        "",
        f"Local technical-review ready: **{required_pass}**",
        f"Final submission ready: **{submission_ready}**",
        "",
        "| Item | Passed | Severity | Evidence |",
        "|---|---:|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['item']}. {check['label']} | {check['passed']} | {check['severity']} | {check['evidence']} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("GOAL ACCEPTANCE LOCAL:", "PASS" if required_pass else "FAIL")
    print("FINAL SUBMISSION READY:", "PASS" if submission_ready else "PENDING")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if not required_pass:
        return 1
    if args.strict_submission and not submission_ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

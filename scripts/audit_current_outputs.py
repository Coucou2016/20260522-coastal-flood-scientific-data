#!/usr/bin/env python3
"""Audit current standalone manuscript/report outputs and core source-table consistency."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "main"
SOURCE_DIR = ROOT / "data" / "figure_source"
FIGURE_MANIFEST = ROOT / "config" / "submission_figure_manifest.json"

EXPECTED_FIGURES = [
    Path(item["png"]).name
    for item in json.loads(FIGURE_MANIFEST.read_text(encoding="utf-8"))["figures"]
]

REQUIRED_FILES = [
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
    "manuscript/repository_deposit_instructions.md",
    "manuscript/current_acceptance_status.md",
    "completion_status.json",
    "logs/goal_acceptance_audit.json",
    "logs/goal_acceptance_audit.md",
]


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        tag = tag.lower()
        if tag == "img":
            self.images.append(attrs_dict)
        elif tag == "script":
            self.scripts.append(attrs_dict)
        elif tag == "link":
            self.links.append(attrs_dict)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(SOURCE_DIR / name)


def check_required_files(errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail(errors, f"Missing required output: {rel}")
        elif path.stat().st_size < 1024:
            fail(errors, f"Output is suspiciously small: {rel} ({path.stat().st_size} bytes)")


def check_html_standalone(errors: list[str], rel: str) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    parser = ImageParser()
    parser.feed(text)

    if len(parser.images) != len(EXPECTED_FIGURES):
        fail(errors, f"{rel} embeds {len(parser.images)} images; expected {len(EXPECTED_FIGURES)}.")

    expected_hashes = {sha256_bytes((FIG_DIR / name).read_bytes()) for name in EXPECTED_FIGURES}
    embedded_hashes: set[str] = set()
    for index, img in enumerate(parser.images, start=1):
        src = img.get("src", "")
        if not src.startswith("data:image/png;base64,"):
            fail(errors, f"{rel} image {index} is not an embedded PNG data URI.")
            continue
        try:
            embedded_hashes.add(sha256_bytes(base64.b64decode(src.split(",", 1)[1], validate=True)))
        except Exception as exc:  # noqa: BLE001
            fail(errors, f"{rel} image {index} has invalid base64: {exc}")

    missing_hashes = expected_hashes - embedded_hashes
    if missing_hashes:
        fail(errors, f"{rel} embedded image hashes do not cover all current figure PNGs.")

    if "file:///" in text or re.search(r"<img[^>]+src=['\"]https?://", text, re.I):
        fail(errors, f"{rel} contains a local or network image reference.")

    external_scripts = [s.get("src", "") for s in parser.scripts if s.get("src")]
    if external_scripts:
        fail(errors, f"{rel} contains external scripts: {external_scripts[:3]}")

    external_stylesheets = [
        link.get("href", "")
        for link in parser.links
        if link.get("rel", "").lower() == "stylesheet" or link.get("href", "").endswith(".css")
    ]
    if external_stylesheets:
        fail(errors, f"{rel} contains external stylesheets: {external_stylesheets[:3]}")

    for forbidden in ["cdn.plot.ly", "echarts", "d3js.org", "unpkg.com", "cdnjs.cloudflare.com"]:
        if forbidden in text:
            fail(errors, f"{rel} contains forbidden external visualization dependency: {forbidden}")


def check_tidal_metadata_consistency(errors: list[str]) -> None:
    tracked = read_csv("TableS_tidal_regime_metadata_source_tracked.csv")
    coverage = read_csv("Fig5_tidal_metadata_coverage_summary.csv")
    tracked_n = int(tracked["source_status"].eq("source_verified").sum())
    coverage_n = int(
        coverage.loc[coverage["source_status"].eq("source_verified"), "n_sites"].iloc[0]
    )
    if tracked_n != 13 or coverage_n != 13:
        fail(errors, f"Expected 13 source-verified tidal stations; got tracked={tracked_n}, coverage={coverage_n}.")

    for rel in ["paper.md", "report.md", "paper.html", "report.html"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "8 个 source-verified tidal stations" in text or "8 source-verified tidal stations" in text:
            fail(errors, f"{rel} still contains the stale eight-station tidal count.")
        if rel.startswith("report") and "13 个 source-verified tidal stations" not in text:
            fail(errors, f"{rel} does not state the 13-station source-verified tidal boundary.")


def check_water_level_math(errors: list[str]) -> None:
    df = read_csv("Fig2_water_level_divergence_with_uncertainty.csv")
    calc = df["coast_rp_rp10_m"] - df["gssr_rp10_m"]
    if not (calc - df["D10_m"]).abs().lt(1e-8).all():
        fail(errors, "Fig2 D10_m is not COAST-RP RP10 minus GSSR RP10.")

    if not df["match_dist_km"].le(6).all():
        fail(errors, "At least one focal COAST-RP match distance exceeds 6 km.")

    if len(df) != 8:
        fail(errors, f"Expected 8 focal water-level rows; found {len(df)}.")


def check_rank_and_archetype_consistency(errors: list[str]) -> None:
    rank = read_csv("Fig6_mask_aware_rank_metrics_fraction_area_samples.csv")
    assoc = read_csv("Fig6_mask_aware_two_sided_permutation_association.csv")
    topk = read_csv("Fig6_mask_aware_topk_overlap_null_envelope.csv")
    block = read_csv("Fig6_mask_aware_sector_block_bootstrap.csv")
    metrics = read_csv("Fig6_mask_aware_terrain_area_metrics.csv")

    unresolved = metrics[~metrics["marine_seed_resolved"].eq(True)]
    if not unresolved.empty and unresolved["mask_connected_2m_lowland_pct"].notna().any():
        fail(errors, "Unresolved marine-seed rows must not be encoded as zero connected response.")
    primary = metrics[
        metrics["marine_seed_resolved"].eq(True)
        & metrics["match_dist_km"].le(6.0)
    ]
    if primary.empty:
        fail(errors, "Primary resolved mask-aware match<=6 km sample is empty.")
    if primary["match_dist_km"].gt(6.0).any():
        fail(errors, "Primary terrain-ranking sample contains a COAST-RP match above 6 km.")

    resolved = metrics[metrics["marine_seed_resolved"].eq(True)].copy()
    identity = (
        resolved["mask_connected_2m_area_km2"]
        + resolved["mask_unconnected_2m_area_km2"]
        - resolved["mask_all_below_2m_area_km2"]
    ).abs()
    if identity.gt(1e-8).any():
        fail(errors, "Connected + unconnected area does not equal all-below area for resolved rows.")

    for _, row in rank.iterrows():
        expected_mismatch = 1.0 - float(row["top_overlap"]) / float(row["top_n"])
        if abs(expected_mismatch - float(row["top_mismatch"])) > 1e-9:
            fail(errors, f"Top mismatch arithmetic error in {row['sample']} / {row['terrain_metric']}.")
        expected_random = 1.0 - float(row["top_n"]) / float(row["n_sites"])
        if abs(expected_random - float(row["random_expected_mismatch"])) > 1e-9:
            fail(errors, f"Random expected mismatch arithmetic error in {row['sample']} / {row['terrain_metric']}.")

    required_assoc = assoc[
        assoc["sample"].eq("primary resolved mask-aware match<=6km")
        & assoc["terrain_metric"].isin(["mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"])
    ]
    if len(required_assoc) != 2:
        fail(errors, "Missing primary fraction/area permutation association rows.")
    for column in ["spearman_two_sided_p", "kendall_two_sided_p"]:
        if not required_assoc[column].between(0.0, 1.0, inclusive="both").all():
            fail(errors, f"Invalid permutation probability in {column}.")

    required_block = block[
        block["sample"].eq("primary resolved mask-aware match<=6km")
        & block["terrain_metric"].isin(["mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"])
    ]
    if len(required_block) != 2:
        fail(errors, "Missing primary coastal-sector block-bootstrap rows.")
    for prefix in ["spearman", "kendall"]:
        if not (
            required_block[f"{prefix}_block_p025"]
            <= required_block[f"{prefix}_block_p500"]
        ).all() or not (
            required_block[f"{prefix}_block_p500"]
            <= required_block[f"{prefix}_block_p975"]
        ).all():
            fail(errors, f"Unordered {prefix} coastal-sector block-bootstrap interval.")

    top20 = topk[
        topk["sample"].eq("primary resolved mask-aware match<=6km")
        & topk["terrain_metric"].eq("mask_connected_2m_lowland_pct")
        & topk["top_fraction"].eq(0.20)
    ]
    if len(top20) != 1:
        fail(errors, "Missing primary top-20% top-k null-envelope row.")
    else:
        row = top20.iloc[0]
        if not 0.0 <= float(row["overlap_low_tail_p"]) <= 1.0:
            fail(errors, "Invalid top-overlap permutation probability.")

    arche = read_csv("Fig6_archetype_map_selection.csv").set_index("station_id")
    fixed = read_csv("Fig6_mask_aware_terrain_area_metrics.csv").set_index("station_id")
    for station_id, row in arche.iterrows():
        if station_id not in fixed.index:
            fail(errors, f"Archetype station not present in mask-aware terrain source: {station_id}")
            continue
        upstream = fixed.loc[station_id]
        if not bool(upstream["marine_seed_resolved"]):
            fail(errors, f"Archetype has unresolved marine seed: {station_id}")
        if float(upstream["match_dist_km"]) > 6.0:
            fail(errors, f"Archetype exceeds primary 6 km match threshold: {station_id}")
        if not str(row.get("selection_rule", "")).strip():
            fail(errors, f"Archetype lacks a recorded selection rule: {station_id}")
        checks = [
            ("coast_rp_rp10_m", row["coast_rp_rp10_m"], upstream["coast_rp_rp10_m"]),
            ("connected_2m_lowland_pct", row["connected_2m_lowland_pct"], upstream["mask_connected_2m_lowland_pct"]),
            ("connected_2m_area_km2", row["connected_2m_area_km2"], upstream["mask_connected_2m_area_km2"]),
        ]
        for name, got, expected in checks:
            if abs(float(got) - float(expected)) > 1e-8:
                fail(errors, f"Archetype {name} mismatch for {station_id}: {got} != {expected}")


def check_terrain_boundary_text(errors: list[str]) -> None:
    mask = read_csv("Fig6_deltadtm_mask_seed_audit.csv").iloc[0]
    manuscript = (ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript.md").read_text(
        encoding="utf-8"
    )
    report = (ROOT / "report.md").read_text(encoding="utf-8")
    if not bool(mask["official_mask_tiles_zip_present"]):
        fail(errors, "Official DeltaDTM mask_tiles.zip is not present.")
    if not bool(mask.get("official_mask_classes_used", False)):
        fail(errors, "Official DeltaDTM mask classes are not marked as used.")
    for required in ["Fig6_mask_aware_terrain_area_metrics.csv", "Fig6_mask_class_counts.csv"]:
        if not (SOURCE_DIR / required).exists():
            fail(errors, f"Missing mask-aware source table: {required}")
    required_phrases = [
        "official DeltaDTM mask",
        "boundary",
        "local DTM cross-check",
    ]
    for phrase in required_phrases:
        if phrase not in manuscript:
            fail(errors, f"Manuscript is missing terrain-boundary phrase: {phrase}")
    for phrase in ["official DeltaDTM mask", "elevation-product and datum sensitivity"]:
        if phrase not in report:
            fail(errors, f"Report is missing terrain-boundary phrase: {phrase}")


def check_reproducibility_package(errors: list[str]) -> None:
    package_dir = ROOT / "reproducibility_package"
    package_zip = ROOT / "reproducibility_package.zip"
    if not package_dir.exists():
        fail(errors, "Missing reproducibility_package directory.")
        return
    if not package_zip.exists() or package_zip.stat().st_size < 1024:
        fail(errors, "Missing or suspiciously small reproducibility_package.zip.")

    required = [
        package_dir / "source_tables" / "processed_station_master_table.csv",
        package_dir / "source_tables" / "Fig6_mask_aware_terrain_area_metrics.csv",
        package_dir / "source_tables" / "Fig6_mask_class_counts.csv",
        package_dir / "source_tables" / "TableS_local_dtm_validation.csv",
        package_dir / "manifests" / "raw_file_hashes.csv",
        package_dir / "manifests" / "package_versions.txt",
        package_dir / "manifests" / "source_data_manifest.json",
        package_dir / "manifests" / "package_manifest.json",
        package_dir / "docs" / "README_reproducibility.md",
        package_dir / "scripts" / "scripts__add_local_dtm_validation.py",
        package_dir / "scripts" / "scripts__build_reproducibility_package.py",
        package_dir / "scripts" / "scripts__audit_goal_acceptance.py",
        package_dir / "scripts" / "scripts__audit_submission_readiness.py",
        package_dir / "scripts" / "scripts__set_submission_links.py",
        package_dir / "scripts" / "scripts__write_current_acceptance_status.py",
        package_dir / "outputs" / "manuscript__repository_deposit_instructions.md",
        package_dir / "outputs" / "manuscript__current_acceptance_status.md",
        package_dir / "outputs" / "completion_status.json",
        package_dir / "outputs" / "logs__goal_acceptance_audit.json",
        package_dir / "outputs" / "logs__goal_acceptance_audit.md",
        package_dir / "docs" / "config__submission_links.json",
        package_dir / "docs" / "config__submission_figure_manifest.json",
        package_dir / "one_command_rebuild.cmd",
    ]
    for path in required:
        if not path.exists() or path.stat().st_size == 0:
            fail(errors, f"Missing reproducibility package artifact: {path.relative_to(ROOT)}")

    master_path = package_dir / "source_tables" / "processed_station_master_table.csv"
    if master_path.exists():
        master = pd.read_csv(master_path)
        if len(master) != 74:
            fail(errors, f"Processed station master table should have 74 rows; found {len(master)}.")
        for col in [
            "station_id",
            "lat",
            "lon",
            "coast_rp_rp10_m",
            "match_dist_km",
            "window_width_km",
            "mask_connected_2m_lowland_pct",
            "mask_connected_2m_area_km2",
            "marine_seed_rule",
        ]:
            if col not in master.columns:
                fail(errors, f"Processed station master table is missing column: {col}")

    raw_path = package_dir / "manifests" / "raw_file_hashes.csv"
    if raw_path.exists():
        raw = pd.read_csv(raw_path)
        if len(raw) < 10:
            fail(errors, "Raw-file hash manifest has too few entries.")
        mask_rows = raw[raw["path"].str.replace("\\\\", "/", regex=False).str.endswith("data/raw/deltadtm/zips/mask_tiles.zip")]
        if len(mask_rows) != 1:
            fail(errors, "Raw-file hash manifest does not include DeltaDTM mask_tiles.zip.")
        expected_raw_paths = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in (ROOT / "data" / "raw").rglob("*")
            if path.is_file()
        }
        recorded_raw_paths = set(raw["path"].astype(str).str.replace("\\", "/", regex=False))
        if recorded_raw_paths != expected_raw_paths:
            fail(
                errors,
                "Raw-file hash manifest does not exactly cover the current data/raw file set "
                f"(missing={len(expected_raw_paths-recorded_raw_paths)}, extra={len(recorded_raw_paths-expected_raw_paths)}).",
            )

    zip_sidecar = ROOT / "reproducibility_package.zip.sha256"
    if not zip_sidecar.exists():
        fail(errors, "Missing reproducibility_package.zip.sha256 sidecar.")
    elif package_zip.exists():
        recorded = zip_sidecar.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(package_zip.read_bytes()).hexdigest()
        if recorded != actual:
            fail(errors, "Reproducibility ZIP SHA-256 sidecar does not match the archive.")

    manifest_path = package_dir / "manifests" / "source_data_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "local_dtm_validation" not in manifest.get("completed_validation_addons", {}):
            fail(errors, "Source data manifest does not record the completed local-DTM cross-check.")
        link_status = manifest.get("repository_link_status", {})
        if not isinstance(link_status, dict):
            fail(errors, "Source data manifest does not include repository_link_status.")
        elif link_status.get("status") == "complete":
            has_reviewer_link = bool(str(link_status.get("private_reviewer_link", "")).strip())
            has_public_pair = bool(str(link_status.get("data_repository_url_or_doi", "")).strip()) and bool(
                str(link_status.get("code_repository_url_or_doi", "")).strip()
            )
            if not (has_reviewer_link or has_public_pair):
                fail(errors, "Repository link status is complete but no usable data/code or reviewer link is recorded.")
        elif "public_repository_doi_or_private_reviewer_link" not in manifest.get("pending_submission_items", {}):
            fail(errors, "Source data manifest does not mark DOI/private reviewer link as pending.")

    local_validation = package_dir / "source_tables" / "TableS_local_dtm_validation.csv"
    if local_validation.exists():
        lv = pd.read_csv(local_validation)
        expected = {
            "sheerness-p015-uk",
            "newlyn-p001-uk",
            "lowestoft-p024-uk",
            "immingham-p026-uk",
            "denhelder-hel-nl",
            "delfzijl-del-nl",
            "hoekvanholla-hvh-nl",
        }
        if set(lv["station_id"]) != expected:
            fail(errors, "Local DTM cross-check table should contain the expected seven-site set.")
        needed = {
            "delta_connected_2m_fraction_pct",
            "local_connected_2m_fraction_pct",
            "local_connected_2m_area_km2",
            "category_changed",
            "connected_pixel_iou_after_reprojection",
        }
        missing = needed - set(lv.columns)
        if missing:
            fail(errors, f"Local DTM cross-check table missing columns: {sorted(missing)}")

    status_path = ROOT / "completion_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") == "finalized":
            fail(errors, "completion_status.json still reports stale finalized status.")
        if status.get("final_submission_gate") != "pending_repository_link" and not status.get(
            "repository_link_status", {}
        ).get("complete"):
            fail(errors, "completion_status.json does not correctly record the pending repository-link gate.")

    goal_audit = ROOT / "logs" / "goal_acceptance_audit.json"
    if goal_audit.exists():
        goal = json.loads(goal_audit.read_text(encoding="utf-8"))
        if not goal.get("local_technical_review_ready"):
            fail(errors, "Goal acceptance audit does not mark the local technical review package as ready.")
        if goal.get("final_submission_ready") and not goal.get("repository_link_status", {}).get("complete"):
            fail(errors, "Goal acceptance audit marks final submission ready without repository link completion.")
    else:
        fail(errors, "Missing logs/goal_acceptance_audit.json. Run scripts/audit_goal_acceptance.py.")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)
    for rel in ["paper.html", "report.html"]:
        check_html_standalone(errors, rel)
    check_tidal_metadata_consistency(errors)
    check_water_level_math(errors)
    check_rank_and_archetype_consistency(errors)
    check_terrain_boundary_text(errors)
    check_reproducibility_package(errors)

    if errors:
        print("CURRENT OUTPUT AUDIT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("CURRENT OUTPUT AUDIT: PASS")
    print("- standalone paper/report outputs exist")
    print("- HTML figures are embedded as current Base64 PNGs with no external scripts/styles")
    print("- tidal source-verified count is consistently 13")
    print("- D10 arithmetic, mask-aware rank diagnostics and Figure 3 archetype source tables are internally consistent")
    print("- official DeltaDTM mask-aware source tables are present and boundary-proxy sensitivity is retained")
    print("- the seven-site elevation-product and datum cross-check table is present")
    print("- reproducibility package contains master table, raw-file hashes, workflow, manifests and current outputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())

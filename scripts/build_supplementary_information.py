#!/usr/bin/env python3
"""Generate self-contained Supplementary Information in MD, HTML and PDF."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from build_standalone_paper import build_html, chrome_executable, data_uri_for_image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"
OUT_MD = ROOT / "supplementary_information.md"
OUT_HTML = ROOT / "supplementary_information.html"
OUT_PDF = ROOT / "supplementary_information.pdf"
MANUSCRIPT_MD = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_supplementary.md"
MANUSCRIPT_HTML = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_supplementary.html"
MANUSCRIPT_PDF = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_supplementary.pdf"


def printable(value: object) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, (float, np.floating)):
        magnitude = abs(float(value))
        if magnitude and magnitude < 0.001:
            return f"{float(value):.3e}"
        return f"{float(value):.3f}"
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text


def table(frame: pd.DataFrame) -> str:
    headers = [str(c).replace("_", " ").replace("|", "\\|") for c in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(printable(v) for v in row) + " |")
    return "\n".join(lines)


def image(number: str, title: str, filename: str) -> str:
    return f"![Supplementary Figure {number}. {title}]({data_uri_for_image(filename)})"


def build_markdown() -> str:
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    rank = pd.read_csv(SOURCE / "Rank_robustness_one_at_a_time.csv")
    block = pd.read_csv(SOURCE / "Spatial_sector_bootstrap_intervals.csv")
    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    return_period = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    moran = pd.read_csv(SOURCE / "Spatial_autocorrelation_moran.csv")
    denominator = pd.read_csv(SOURCE / "Denominator_geometry_68stations.csv")
    denominator_stats = pd.read_csv(SOURCE / "Denominator_adjusted_associations.csv")
    topology = pd.read_csv(SOURCE / "Topology_membership_changes.csv")
    topology_summary = pd.read_csv(SOURCE / "Topology_sensitivity_summary.csv")
    influence = pd.read_csv(SOURCE / "Station_influence_jackknife.csv")
    sector_specific = pd.read_csv(SOURCE / "Sector_specific_associations.csv")
    match_audit = pd.read_csv(SOURCE / "Match_distance_audit_74stations.csv")
    gssr_audit = pd.read_csv(SOURCE / "GSSR_metadata_field_audit.csv")
    tidal_plotted = pd.read_csv(SOURCE / "FigS1_tidal_source_audit.csv")
    leave = pd.read_csv(SOURCE / "Leave_one_coastal_sector_out.csv")
    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")
    selection = pd.read_csv(SOURCE / "Fig3_predefined_site_selection.csv")
    product = pd.read_csv(SOURCE / "DeltaDTM_v1_1_product_version_audit.csv")
    flow = pd.read_csv(SOURCE / "Primary_sample_flow.csv")
    water = pd.read_csv(SOURCE / "Fig2_water_level_divergence_with_uncertainty.csv")
    tidal = pd.read_csv(SOURCE / "TableS_tidal_regime_metadata_source_tracked.csv")

    primary_table = primary[
        [
            "station_id",
            "station",
            "coastal_sector",
            "lat",
            "lon",
            "coast_rp_rp10_m",
            "match_dist_km",
            "below_reference_land_pct",
            "conditional_connectivity_pct",
            "connected_reference_land_pct",
            "connected_area_km2",
        ]
    ].sort_values("coast_rp_rp10_m", ascending=False)
    primary_table.columns = [
        "Station ID",
        "Station",
        "Coastal sector",
        "Latitude",
        "Longitude",
        "COAST-RP RP10 (m)",
        "Match distance (km)",
        "Below-2 m land share (%)",
        "Conditional connection (%)",
        "Connected land share (%)",
        "Connected area (km2)",
    ]

    base_setting = "primary:10km,2m,4n,adaptive,match<=6km"
    primary_stats = rank[rank["setting"].eq(base_setting)][
        [
            "terrain_metric",
            "n_sites",
            "spearman",
            "kendall",
            "permutation_two_sided_p",
            "top_n",
            "top_overlap",
            "top_overlap_expected_independent",
        ]
    ].merge(
        block[
            [
                "terrain_metric",
                "spearman_sector_bootstrap_p025",
                "spearman_sector_bootstrap_p975",
            ]
        ],
        on="terrain_metric",
    ).merge(
        return_period[return_period["return_period_years"].eq(10)][
            [
                "terrain_metric",
                "sector_adjusted_rank_association",
                "sector_stratified_permutation_two_sided_p",
            ]
        ],
        on="terrain_metric",
    )
    primary_stats.columns = [
        "Terrain metric",
        "n",
        "Spearman rho",
        "Kendall tau",
        "Two-sided label-permutation p",
        "Top-set n",
        "Observed overlap",
        "Expected independent overlap",
        "Sector bootstrap 2.5%",
        "Sector bootstrap 97.5%",
        "Sector-adjusted rank association",
        "Within-sector permutation p",
    ]

    robustness = rank[
        [
            "setting",
            "terrain_metric",
            "n_sites",
            "spearman",
            "kendall",
            "permutation_two_sided_p",
            "terrain_rank_spearman_vs_primary",
            "top20_jaccard_vs_primary",
            "top20_membership_changes_vs_primary",
        ]
    ]
    robustness.columns = [
        "Setting",
        "Terrain metric",
        "n",
        "Spearman rho",
        "Kendall tau",
        "Two-sided p",
        "Terrain-rank rho vs primary",
        "Top-20% Jaccard vs primary",
        "Top-20% membership changes",
    ]

    topk_table = topk[topk["top_share_pct"].isin([10, 15, 20, 25, 30, 35, 40])].drop(columns=["note"]).copy()

    leave_table = leave[
        ["terrain_metric", "omitted_sector", "omitted_n", "n_sites", "spearman", "kendall", "permutation_two_sided_p", "top_n", "top_overlap"]
    ]
    leave_table.columns = ["Terrain metric", "Omitted sector", "Omitted n", "Remaining n", "Spearman rho", "Kendall tau", "Two-sided p", "Top n", "Overlap"]

    local_table = local[
        [
            "station",
            "local_dtm_source",
            "local_dtm_vertical_datum_note",
            "delta_connected_2m_reference_land_pct",
            "local_connected_2m_reference_land_pct",
            "delta_conditional_connectivity_2m_pct",
            "local_conditional_connectivity_2m_pct",
            "delta_connected_2m_area_km2",
            "local_connected_2m_area_km2",
            "connected_pixel_iou_after_reprojection",
            "continuous_elevation_resampling",
        ]
    ]
    local_table.columns = [
        "Station",
        "Local terrain product",
        "Native datum",
        "Delta connected share (%)",
        "Local connected share (%)",
        "Delta conditional connection (%)",
        "Local conditional connection (%)",
        "Delta area (km2)",
        "Local area (km2)",
        "Connected-mask IoU",
        "Elevation resampling",
    ]

    selection_table = selection[
        [
            "station",
            "figure3_role",
            "selection_rule",
            "coast_rp_rp10_m",
            "water_rank",
            "terrain_rank",
            "below_reference_land_pct",
            "conditional_connectivity_pct",
            "connected_reference_land_pct",
            "connected_area_km2",
        ]
    ]
    selection_table.columns = [
        "Station",
        "Figure 3 role",
        "Recorded selection rule",
        "RP10 (m)",
        "Water rank",
        "Terrain rank",
        "Below-2 m share (%)",
        "Conditional connection (%)",
        "Connected share (%)",
        "Connected area (km2)",
    ]

    water_table = water[
        [
            "full_label",
            "gssr_rp10_m",
            "gssr_rp10_bootstrap_p025_m",
            "gssr_rp10_bootstrap_p975_m",
            "gssr_predint_rp10_lower_m",
            "gssr_predint_rp10_upper_m",
            "coast_rp_rp10_m",
            "within5km_min_rp10_m",
            "within5km_max_rp10_m",
            "D10_m",
            "spring_tidal_range_m",
            "source_status",
        ]
    ]
    water_table.columns = [
        "Station",
        "GSSR empirical RP10 (m)",
        "Bootstrap 2.5%",
        "Bootstrap 97.5%",
        "GSSR lower-bound RP10",
        "GSSR upper-bound RP10",
        "COAST-RP RP10 (m)",
        "Within-5 km minimum",
        "Within-5 km maximum",
        "D10 cross-product difference (m)",
        "Tidal range (m)",
        "Tidal source status",
    ]

    tidal_table = tidal[
        ["station", "tidal_range_metric", "spring_tidal_range_m", "source_status", "source", "source_url", "notes"]
    ]
    tidal_table.columns = ["Station", "Metric", "Range (m)", "Source status", "Source", "URL", "Notes"]

    rp_table = return_period[
        [
            "return_period_years",
            "terrain_metric_label",
            "n_sites",
            "spearman",
            "kendall",
            "sector_adjusted_rank_association",
            "sector_stratified_permutation_two_sided_p",
            "top20_observed_overlap",
            "sector_stratified_top20_lower_tail_p",
        ]
    ].copy()
    rp_table.columns = ["Return period (years)", "Terrain metric", "n", "Spearman rho", "Kendall tau", "Sector-adjusted rank association", "Within-sector p", "Top-20% overlap", "Spatial-null lower-tail p"]

    denominator_table = denominator[
        [
            "station",
            "window_area_km2",
            "reference_land_area_km2",
            "represented_land_window_pct",
            "below_area_km2",
            "connected_area_km2",
            "connected_window_pct",
        ]
    ].sort_values("station")
    denominator_table.columns = ["Station", "Nominal window area (km2)", "Represented land area (km2)", "Represented land (%)", "Below-2 m area (km2)", "Connected area (km2)", "Connected window share (%)"]

    influence_table = influence.loc[
        influence.groupby("terrain_metric")["delta_spearman"].apply(lambda values: values.abs().idxmax())
    ][["terrain_metric_label", "omitted_station", "omitted_sector", "full_spearman", "leave_one_out_spearman", "delta_spearman"]]
    influence_table.columns = ["Terrain metric", "Most influential omitted station", "Sector", "Full rho", "Leave-one-out rho", "Change in rho"]

    topology_change_table = topology[topology["membership_change"].ne("unchanged")][
        ["station", "terrain_metric", "four_neighbour_value", "eight_neighbour_value", "membership_change"]
    ]
    topology_change_table.columns = ["Station", "Terrain metric", "4-neighbour value", "8-neighbour value", "Membership change"]

    excluded_match_table = match_audit[~match_audit["included_in_primary_match_sample"]][
        ["station", "lat", "lon", "coast_rp_source_station_id", "recomputed_match_dist_km", "match_exclusion_reason"]
    ]
    excluded_match_table.columns = ["Station", "Latitude", "Longitude", "COAST-RP point", "Distance (km)", "Reason"]

    tidal_plotted_table = tidal_plotted[
        ["station", "spring_tidal_range_m", "coast_rp_rp10_m", "connected_reference_land_pct", "source", "source_url"]
    ]
    tidal_plotted_table.columns = ["Station", "Spring tidal range (m)", "COAST-RP RP10 (m)", "Connected land share (%)", "Source", "URL"]

    parts = [
        "# Supplementary Information",
        "",
        "## Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network",
        "",
        "**Authors and affiliations:** 待补充",
        "",
        "This Supplementary Information is generated from the same frozen source tables as the manuscript. Legacy degree-window, 15 m denominator and category-based tables are intentionally excluded.",
        "",
        "## Supplementary Methods",
        "",
        "The complete terrain grid contains 74 stations and 40 configurations per station (2,960 rows). The primary configuration is a 10 km window, standardized 2 m EGM2008 terrain threshold, four-neighbour graph, adaptive official-mask marine seed and COAST-RP match within 6 km. Only finite official-mask class-0 terrain enters the reference-land denominator. Internal outside-support value 254 and official classes 1, 2, 3 and 255 are excluded. Sector resampling, within-sector permutation and sector adjustment use the same six geographic identifiers shown in Fig. 1.",
        "",
        "The local terrain comparison retains each source product's native vertical datum. Continuous elevation was downscaled by the provider WCS; the service interpolation kernel was not controlled by the study code. Categorical masks and the connected mask used for intersection-over-union were reprojected by nearest neighbour to the local WCS grid.",
        "",
        "## Supplementary Figures",
        "",
        image("S1", "Source-verified tidal context", "FigS1_water_level_definition.png"),
        "",
        "All 13 source-verified stations are plotted once. Tidal range covaries strongly with storm-tide magnitude but not with the standardized connected-terrain share in this small exploratory subset.",
        "",
        image("S2", "Predictor-consistency diagnostic for focal GSSR series", "FigS2_process_coherence.png"),
        "",
        "The atmospheric predictors overlap with the reconstruction framework. This panel is therefore not independent validation or extreme-event skill assessment and is not used in the terrain analysis.",
        "",
        image("S3", "Standardized static terrain gallery", "FigS3_connectivity_gallery.png"),
        "",
        "Every panel uses the same fixed 10 km window, official mask and 2 m EGM2008 threshold. Blue and orange cells retain their original raster footprint.",
        "",
        image("S4", "Local-DTM product, datum and resampling sensitivity", "FigS4_elevation_product_datum_sensitivity.png"),
        "",
        "The three vertical references are not harmonized. The figure combines elevation-product, native-datum and provider-resampling effects and is not a validation result.",
        "",
        image("S5", "COAST-RP nearest-point matching audit", "FigS5_coastrp_match_audit.png"),
        "",
        "All 74 candidate gauge-to-product pairs are retained in the source table. The six excluded Loire estuary stations lie 6.90-39.42 km from the nearest COAST-RP point.",
        "",
        "## Supplementary Tables",
        "",
        "**Supplementary Table S1. Frozen sample flow.**",
        "",
        table(flow),
        "",
        "**Supplementary Table S2. DeltaDTM v1.1.1 product-version and mask-fill audit.**",
        "",
        table(product),
        "",
        "**Supplementary Table S3. Primary association, spatial interval and top-set statistics.**",
        "",
        table(primary_stats),
        "",
        "**Supplementary Table S4. COAST-RP return-period sensitivity with spatially constrained inference.**",
        "",
        table(rp_table),
        "",
        "**Supplementary Table S5. Full 68-station primary source table.**",
        "",
        table(primary_table),
        "",
        "**Supplementary Table S6. Window support and alternative connected-window denominator.**",
        "",
        table(denominator_table),
        "",
        "**Supplementary Table S7. Denominator-adjusted associations.**",
        "",
        table(denominator_stats),
        "",
        "**Supplementary Table S8. One-at-a-time full-sample robustness grid.**",
        "",
        table(robustness),
        "",
        "**Supplementary Table S9. Spatially constrained top-k overlap null curves, with nonspatial hypergeometric comparators.**",
        "",
        table(topk_table),
        "",
        "The table reports five-percentage-point intervals for readability. The machine-readable source file retains every integer top-set share from 10% to 40%. Hypergeometric values are descriptive nonspatial comparators; inference uses within-sector permutations.",
        "",
        "**Supplementary Table S10. Leave-one-coastal-sector-out calculations.**",
        "",
        table(leave_table),
        "",
        "**Supplementary Table S11. Sector-specific associations.**",
        "",
        table(sector_specific),
        "",
        "**Supplementary Table S12. Moran spatial-autocorrelation diagnostics.**",
        "",
        table(moran),
        "",
        "**Supplementary Table S13. Maximum leave-one-station influence by terrain metric.**",
        "",
        table(influence_table),
        "",
        "**Supplementary Table S14. Four- versus eight-neighbour summary.**",
        "",
        table(topology_summary),
        "",
        "**Supplementary Table S15. Stations whose top-20% membership changes between four and eight neighbours.**",
        "",
        table(topology_change_table),
        "",
        "**Supplementary Table S16. Recorded Figure 3 case-selection rules and values.**",
        "",
        table(selection_table),
        "",
        "**Supplementary Table S17. Seven-site local-DTM product, datum and resampling cross-check.**",
        "",
        table(local_table),
        "",
        "**Supplementary Table S18. Excluded COAST-RP nearest-point matches.**",
        "",
        table(excluded_match_table),
        "",
        "**Supplementary Table S19. Focal GSSR and COAST-RP product-context diagnostics.**",
        "",
        table(water_table),
        "",
        "**Supplementary Table S20. Source-verified tidal stations plotted in Supplementary Figure S1.**",
        "",
        table(tidal_plotted_table),
        "",
        "**Supplementary Table S21. Complete tidal metadata source audit.**",
        "",
        table(tidal_table),
        "",
        "**Supplementary Table S22. GSSR metadata-field and filter audit.**",
        "",
        table(gssr_audit),
        "",
        "## Supplementary Data provenance",
        "",
        "Machine-readable source files for all tables are retained under `data/figure_source/`. The scientific-integrity review records current hashes, invariants and known external-deposit placeholders. References are listed in the main manuscript.",
        "",
    ]
    return "\n".join(parts)


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = chrome_executable()
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        cwd=ROOT,
        check=True,
        timeout=180,
    )
    if not pdf_path.exists() or pdf_path.stat().st_size < 100_000:
        raise RuntimeError(f"Suspicious PDF output: {pdf_path}")


def main() -> int:
    markdown = build_markdown()
    html = build_html(markdown)
    html = html.replace(
        "</head>",
        """<style>
@media print {
  p:has(+ .scroll-table) { break-after: avoid-page; }
  .scroll-table table { break-inside: auto; }
  .scroll-table thead { display: table-header-group; }
  .scroll-table tr { break-inside: avoid; }
}
</style></head>""",
    )
    OUT_MD.write_text(markdown, encoding="utf-8")
    OUT_HTML.write_text(html, encoding="utf-8")
    MANUSCRIPT_MD.write_text(markdown, encoding="utf-8")
    MANUSCRIPT_HTML.write_text(html, encoding="utf-8")
    render_pdf(OUT_HTML, OUT_PDF)
    shutil.copyfile(OUT_PDF, MANUSCRIPT_PDF)
    print(f"Wrote {OUT_MD}, {OUT_HTML}, and {OUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

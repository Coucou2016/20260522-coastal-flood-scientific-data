from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"
COAST_RP = ROOT / "data" / "raw" / "coast_rp" / "extracted" / "COAST-RP.nc"
GSSR_METADATA = ROOT / "data" / "raw" / "gssr" / "metadata" / "eraint.geojson"

RETURN_PERIODS = (2, 5, 10, 25, 50, 100)
METRICS = (
    "below_reference_land_pct",
    "conditional_connectivity_pct",
    "connected_reference_land_pct",
    "connected_area_km2",
    "connected_window_pct",
)
METRIC_LABELS = {
    "below_reference_land_pct": "lowland_prevalence",
    "conditional_connectivity_pct": "conditional_connectivity",
    "connected_reference_land_pct": "connected_lowland_share",
    "connected_area_km2": "connected_area",
    "connected_window_pct": "connected_window_share",
}
SEED = 20260829
N_PERMUTATIONS = 10_000


def haversine_matrix(lat_a: np.ndarray, lon_a: np.ndarray, lat_b: np.ndarray, lon_b: np.ndarray) -> np.ndarray:
    lat1 = np.radians(np.asarray(lat_a, dtype=float))[:, None]
    lon1 = np.radians(np.asarray(lon_a, dtype=float))[:, None]
    lat2 = np.radians(np.asarray(lat_b, dtype=float))[None, :]
    lon2 = np.radians(np.asarray(lon_b, dtype=float))[None, :]
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def residualize(values: np.ndarray, controls: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    controls = np.asarray(controls, dtype=float)
    if controls.ndim == 1:
        controls = controls[:, None]
    x = np.column_stack([np.ones(len(values)), controls])
    beta, *_ = np.linalg.lstsq(x, values, rcond=None)
    return values - x @ beta


def sector_design(sectors: pd.Series) -> np.ndarray:
    return pd.get_dummies(sectors.astype(str), drop_first=True, dtype=float).to_numpy(float)


def sector_permutations(values: np.ndarray, sectors: np.ndarray, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    result = np.empty((n_perm, len(values)), dtype=float)
    groups = [np.flatnonzero(sectors == sector) for sector in np.unique(sectors)]
    for i in range(n_perm):
        row = values.copy()
        for idx in groups:
            row[idx] = values[idx][rng.permutation(len(idx))]
        result[i] = row
    return result


def rank_correlations_against_fixed(x: np.ndarray, permuted_y: np.ndarray) -> np.ndarray:
    rx = stats.rankdata(x).astype(float)
    rx -= rx.mean()
    ry = np.apply_along_axis(stats.rankdata, 1, permuted_y).astype(float)
    ry -= ry.mean(axis=1, keepdims=True)
    numerator = ry @ rx
    denominator = np.sqrt(np.sum(ry * ry, axis=1) * np.sum(rx * rx))
    return np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 0)


def two_sided_p(null: np.ndarray, observed: float, centre: float = 0.0) -> float:
    return float((1 + np.sum(np.abs(null - centre) >= abs(observed - centre))) / (len(null) + 1))


def extract_return_periods(primary: pd.DataFrame) -> pd.DataFrame:
    with xr.open_dataset(COAST_RP) as ds:
        coast_lat = ds["station_y_coordinate"].values.astype(float)
        coast_lon = ds["station_x_coordinate"].values.astype(float)
        coast_ids = ds["station_id"].values.astype(str)
        distances = haversine_matrix(primary["lat"].to_numpy(), primary["lon"].to_numpy(), coast_lat, coast_lon)
        nearest = distances.argmin(axis=1)
        rows = primary[["station_id", "station", "lat", "lon", "coastal_sector", "match_dist_km"]].copy()
        rows["coast_rp_source_station_id"] = coast_ids[nearest]
        rows["coast_rp_source_lat"] = coast_lat[nearest]
        rows["coast_rp_source_lon"] = coast_lon[nearest]
        rows["recomputed_match_dist_km"] = distances[np.arange(len(rows)), nearest]
        for rp in RETURN_PERIODS:
            rows[f"coast_rp_rp{rp}_m"] = ds[f"storm_tide_rp_{rp:04d}"].values.astype(float)[nearest]
    check = np.max(np.abs(rows["coast_rp_rp10_m"].to_numpy() - primary["coast_rp_rp10_m"].to_numpy()))
    distance_check = np.max(np.abs(rows["recomputed_match_dist_km"].to_numpy() - primary["match_dist_km"].to_numpy()))
    if check > 1e-5 or distance_check > 0.02:
        raise AssertionError(f"COAST-RP extraction mismatch: RP10={check:.6g}, distance={distance_check:.6g}")
    rows.to_csv(SOURCE / "TableS_coastrp_multi_return_period_68stations.csv", index=False)
    return rows


def return_period_diagnostics(primary: pd.DataFrame, rp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = primary.drop(columns=["coast_rp_rp10_m"]).merge(
        rp.drop(columns=["station", "lat", "lon", "coastal_sector", "match_dist_km"]),
        on="station_id",
    )
    sectors = merged["coastal_sector"].astype(str).to_numpy()
    sector_x = sector_design(merged["coastal_sector"])
    rows: list[dict[str, object]] = []
    top_rows: list[dict[str, object]] = []
    for rp_value in RETURN_PERIODS:
        water = merged[f"coast_rp_rp{rp_value}_m"].to_numpy(float)
        for metric_index, metric in enumerate(METRICS):
            terrain = merged[metric].to_numpy(float)
            valid = np.isfinite(water) & np.isfinite(terrain)
            x = water[valid]
            y = terrain[valid]
            sec = sectors[valid]
            design = sector_x[valid]
            observed_s = float(stats.spearmanr(x, y).statistic)
            observed_k = float(stats.kendalltau(x, y).statistic)
            rng = np.random.default_rng(SEED + rp_value * 100 + metric_index)
            permuted = sector_permutations(y, sec, N_PERMUTATIONS, rng)
            null_s = rank_correlations_against_fixed(x, permuted)
            rx = stats.rankdata(x)
            ry = stats.rankdata(y)
            adjusted = float(stats.pearsonr(residualize(rx, design), residualize(ry, design)).statistic)
            k = int(math.ceil(0.20 * len(x)))
            water_top = np.argpartition(x, -k)[-k:]
            terrain_top = np.argpartition(y, -k)[-k:]
            observed_overlap = int(len(np.intersect1d(water_top, terrain_top)))
            null_overlap = np.sum(np.isin(np.argsort(permuted, axis=1)[:, -k:], water_top), axis=1)
            rows.append(
                {
                    "return_period_years": rp_value,
                    "terrain_metric": metric,
                    "terrain_metric_label": METRIC_LABELS[metric],
                    "n_sites": len(x),
                    "spearman": observed_s,
                    "kendall": observed_k,
                    "sector_adjusted_rank_association": adjusted,
                    "sector_stratified_permutation_two_sided_p": two_sided_p(null_s, observed_s),
                    "sector_stratified_null_spearman_q025": float(np.quantile(null_s, 0.025)),
                    "sector_stratified_null_spearman_median": float(np.quantile(null_s, 0.5)),
                    "sector_stratified_null_spearman_q975": float(np.quantile(null_s, 0.975)),
                    "top20_n": k,
                    "top20_observed_overlap": observed_overlap,
                    "top20_observed_mismatch_pct": 100.0 * (1.0 - observed_overlap / k),
                    "sector_stratified_top20_null_median": float(np.median(null_overlap)),
                    "sector_stratified_top20_null_q025": float(np.quantile(null_overlap, 0.025)),
                    "sector_stratified_top20_null_q975": float(np.quantile(null_overlap, 0.975)),
                    "sector_stratified_top20_lower_tail_p": float((1 + np.sum(null_overlap <= observed_overlap)) / (N_PERMUTATIONS + 1)),
                    "n_permutations": N_PERMUTATIONS,
                }
            )
            if rp_value == 10 and metric == "connected_reference_land_pct":
                for pct in range(10, 41):
                    top_n = int(math.ceil(pct / 100.0 * len(x)))
                    wtop = np.argpartition(x, -top_n)[-top_n:]
                    ttop = np.argpartition(y, -top_n)[-top_n:]
                    observed = int(len(np.intersect1d(wtop, ttop)))
                    null = np.sum(np.isin(np.argsort(permuted, axis=1)[:, -top_n:], wtop), axis=1)
                    hyper = stats.hypergeom(len(x), top_n, top_n)
                    top_rows.append(
                        {
                            "top_share_pct": pct,
                            "n_sites": len(x),
                            "top_n": top_n,
                            "observed_overlap": observed,
                            "sector_stratified_null_median": float(np.median(null)),
                            "sector_stratified_null_q025": float(np.quantile(null, 0.025)),
                            "sector_stratified_null_q975": float(np.quantile(null, 0.975)),
                            "sector_stratified_lower_tail_p": float((1 + np.sum(null <= observed)) / (N_PERMUTATIONS + 1)),
                            "nonspatial_hypergeometric_mean": float(hyper.mean()),
                            "nonspatial_hypergeometric_q025": float(hyper.ppf(0.025)),
                            "nonspatial_hypergeometric_q975": float(hyper.ppf(0.975)),
                            "note": "The hypergeometric values are descriptive nonspatial comparators; inference uses within-sector permutations.",
                        }
                    )
    output = pd.DataFrame(rows)
    top_output = pd.DataFrame(top_rows)
    output.to_csv(SOURCE / "Return_period_sensitivity.csv", index=False)
    top_output.to_csv(SOURCE / "Topk_spatial_null_curves.csv", index=False)
    return output, top_output


def jackknife_and_sectors(primary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    influence: list[dict[str, object]] = []
    sector_rows: list[dict[str, object]] = []
    water = primary["coast_rp_rp10_m"].to_numpy(float)
    for metric in METRICS:
        terrain = primary[metric].to_numpy(float)
        full_s = float(stats.spearmanr(water, terrain).statistic)
        full_k = float(stats.kendalltau(water, terrain).statistic)
        for i, row in primary.reset_index(drop=True).iterrows():
            keep = np.ones(len(primary), dtype=bool)
            keep[i] = False
            s = float(stats.spearmanr(water[keep], terrain[keep]).statistic)
            k = float(stats.kendalltau(water[keep], terrain[keep]).statistic)
            influence.append(
                {
                    "terrain_metric": metric,
                    "terrain_metric_label": METRIC_LABELS[metric],
                    "omitted_station_id": row["station_id"],
                    "omitted_station": row["station"],
                    "omitted_sector": row["coastal_sector"],
                    "full_spearman": full_s,
                    "leave_one_out_spearman": s,
                    "delta_spearman": s - full_s,
                    "full_kendall": full_k,
                    "leave_one_out_kendall": k,
                    "delta_kendall": k - full_k,
                }
            )
        for sector, group in primary.groupby("coastal_sector", sort=True):
            record: dict[str, object] = {
                "coastal_sector": sector,
                "terrain_metric": metric,
                "terrain_metric_label": METRIC_LABELS[metric],
                "n_sites": len(group),
            }
            if len(group) >= 4:
                record["spearman"] = float(stats.spearmanr(group["coast_rp_rp10_m"], group[metric]).statistic)
                record["kendall"] = float(stats.kendalltau(group["coast_rp_rp10_m"], group[metric]).statistic)
                record["status"] = "estimated"
            else:
                record["spearman"] = np.nan
                record["kendall"] = np.nan
                record["status"] = "insufficient_n_lt4"
            sector_rows.append(record)
    influence_frame = pd.DataFrame(influence)
    sector_frame = pd.DataFrame(sector_rows)
    influence_frame.to_csv(SOURCE / "Station_influence_jackknife.csv", index=False)
    sector_frame.to_csv(SOURCE / "Sector_specific_associations.csv", index=False)
    return influence_frame, sector_frame


def moran_i(values: np.ndarray, weights: np.ndarray) -> float:
    z = np.asarray(values, dtype=float) - np.nanmean(values)
    s0 = weights.sum()
    return float(len(z) / s0 * np.sum(weights * np.outer(z, z)) / np.sum(z * z))


def spatial_autocorrelation(primary: pd.DataFrame) -> pd.DataFrame:
    distance = haversine_matrix(primary["lat"].to_numpy(), primary["lon"].to_numpy(), primary["lat"].to_numpy(), primary["lon"].to_numpy())
    rows: list[dict[str, object]] = []
    variables = {"coast_rp_rp10_m": primary["coast_rp_rp10_m"].to_numpy(float)}
    variables.update({metric: primary[metric].to_numpy(float) for metric in METRICS})
    for threshold in (150.0, 250.0):
        binary = ((distance > 0) & (distance <= threshold)).astype(float)
        zero_rows = binary.sum(axis=1) == 0
        if np.any(zero_rows):
            nearest = np.where(distance > 0, distance, np.inf).argmin(axis=1)
            binary[np.flatnonzero(zero_rows), nearest[zero_rows]] = 1.0
        weights = binary / binary.sum(axis=1, keepdims=True)
        for j, (name, values) in enumerate(variables.items()):
            observed = moran_i(values, weights)
            rng = np.random.default_rng(SEED + int(threshold) * 10 + j)
            null = np.array([moran_i(rng.permutation(values), weights) for _ in range(4_999)])
            expected = -1.0 / (len(values) - 1)
            rows.append(
                {
                    "variable": name,
                    "distance_threshold_km": threshold,
                    "moran_i": observed,
                    "expected_i_under_randomization": expected,
                    "permutation_two_sided_p": two_sided_p(null, observed, centre=expected),
                    "null_q025": float(np.quantile(null, 0.025)),
                    "null_q975": float(np.quantile(null, 0.975)),
                    "weight_definition": "row-standardized binary great-circle distance; isolated stations linked to nearest neighbour",
                    "n_permutations": 4_999,
                }
            )
    output = pd.DataFrame(rows)
    output.to_csv(SOURCE / "Spatial_autocorrelation_moran.csv", index=False)
    return output


def denominator_diagnostics(primary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mask = pd.read_csv(SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    mask_cols = [
        "station_id",
        "mask_ocean_area_km2",
        "mask_river_area_km2",
        "mask_lake_area_km2",
        "mask_clipped_255_area_km2",
        "mask_outside_support_area_km2",
        "mask_land_area_km2",
    ]
    frame = primary.merge(mask[mask_cols], on="station_id", how="left")
    if "window_area_km2" not in frame:
        frame["window_area_km2"] = (
            frame["mask_ocean_area_km2"]
            + frame["mask_river_area_km2"]
            + frame["mask_lake_area_km2"]
            + frame["mask_clipped_255_area_km2"]
            + frame["mask_outside_support_area_km2"]
            + frame["mask_land_area_km2"]
        )
    frame["represented_land_window_pct"] = 100.0 * frame["reference_land_area_km2"] / frame["window_area_km2"]
    frame["connected_window_pct"] = 100.0 * frame["connected_area_km2"] / frame["window_area_km2"]
    frame["below_window_pct"] = 100.0 * frame["below_area_km2"] / frame["window_area_km2"]
    frame.to_csv(SOURCE / "Denominator_geometry_68stations.csv", index=False)

    rows: list[dict[str, object]] = []
    land = frame["represented_land_window_pct"].to_numpy(float)
    water = frame["coast_rp_rp10_m"].to_numpy(float)
    controls = stats.rankdata(land)
    for metric in METRICS:
        terrain = frame[metric].to_numpy(float)
        raw = float(stats.spearmanr(water, terrain).statistic)
        partial = float(
            stats.pearsonr(
                residualize(stats.rankdata(water), controls),
                residualize(stats.rankdata(terrain), controls),
            ).statistic
        )
        rows.append(
            {
                "terrain_metric": metric,
                "terrain_metric_label": METRIC_LABELS[metric],
                "n_sites": len(frame),
                "raw_spearman_water_vs_metric": raw,
                "partial_spearman_controlling_represented_land_fraction": partial,
                "spearman_metric_vs_represented_land_fraction": float(stats.spearmanr(terrain, land).statistic),
                "spearman_water_vs_represented_land_fraction": float(stats.spearmanr(water, land).statistic),
            }
        )
    output = pd.DataFrame(rows)
    output.to_csv(SOURCE / "Denominator_adjusted_associations.csv", index=False)
    return frame, output


def topology_diagnostics(primary: pd.DataFrame, detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_filter = (
        detail["window_width_km"].eq(10.0)
        & detail["eta_m"].eq(2.0)
        & detail["seed_rule"].eq("official_adaptive")
        & detail["elevation_offset_m"].eq(0.0)
        & detail["match_dist_km"].le(6.0)
    )
    records: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []
    for metric in ("connected_reference_land_pct", "connected_area_km2", "conditional_connectivity_pct"):
        four = detail[base_filter & detail["neighbours"].eq(4)].set_index("station_id")
        eight = detail[base_filter & detail["neighbours"].eq(8)].set_index("station_id")
        ids = primary["station_id"].tolist()
        f = four.loc[ids, metric]
        e = eight.loc[ids, metric]
        k = int(math.ceil(0.2 * len(ids)))
        ftop = set(f.nlargest(k).index)
        etop = set(e.nlargest(k).index)
        for station_id in ids:
            records.append(
                {
                    "station_id": station_id,
                    "station": primary.set_index("station_id").loc[station_id, "station"],
                    "terrain_metric": metric,
                    "four_neighbour_value": float(f.loc[station_id]),
                    "eight_neighbour_value": float(e.loc[station_id]),
                    "eight_minus_four": float(e.loc[station_id] - f.loc[station_id]),
                    "four_neighbour_top20": station_id in ftop,
                    "eight_neighbour_top20": station_id in etop,
                    "membership_change": "entered_under_8n" if station_id in etop - ftop else "left_under_8n" if station_id in ftop - etop else "unchanged",
                }
            )
        summary.append(
            {
                "terrain_metric": metric,
                "n_sites": len(ids),
                "rank_spearman_4n_vs_8n": float(stats.spearmanr(f, e).statistic),
                "top20_n": k,
                "top20_overlap": len(ftop & etop),
                "membership_changes": len(ftop ^ etop),
                "maximum_eight_minus_four": float((e - f).max()),
                "median_eight_minus_four": float((e - f).median()),
            }
        )
    records_frame = pd.DataFrame(records)
    summary_frame = pd.DataFrame(summary)
    records_frame.to_csv(SOURCE / "Topology_membership_changes.csv", index=False)
    summary_frame.to_csv(SOURCE / "Topology_sensitivity_summary.csv", index=False)
    return records_frame, summary_frame


def match_audit() -> pd.DataFrame:
    audit = pd.read_csv(SOURCE / "Fig5_station_candidate_audit.csv")
    with xr.open_dataset(COAST_RP) as ds:
        coast_lat = ds["station_y_coordinate"].values.astype(float)
        coast_lon = ds["station_x_coordinate"].values.astype(float)
        coast_ids = ds["station_id"].values.astype(str)
        distances = haversine_matrix(audit["lat"].to_numpy(), audit["lon"].to_numpy(), coast_lat, coast_lon)
        nearest = distances.argmin(axis=1)
        audit["coast_rp_source_station_id"] = coast_ids[nearest]
        audit["coast_rp_source_lat"] = coast_lat[nearest]
        audit["coast_rp_source_lon"] = coast_lon[nearest]
        audit["recomputed_match_dist_km"] = distances[np.arange(len(audit)), nearest]
    if np.max(np.abs(audit["recomputed_match_dist_km"] - audit["match_dist_km"])) > 0.02:
        raise AssertionError("Candidate-audit COAST-RP distances do not reproduce from the raw product.")
    audit["included_in_primary_match_sample"] = audit["match_dist_km"].le(6.0)
    audit["match_exclusion_reason"] = np.where(
        audit["included_in_primary_match_sample"],
        "included_match_le6km",
        "excluded_nearest_coast_rp_point_gt6km",
    )
    audit["threshold_note"] = "The 6 km rule is a pre-specified extraction screen, not an along-coast representativeness guarantee."
    audit.to_csv(SOURCE / "Match_distance_audit_74stations.csv", index=False)
    hist = pd.DataFrame(
        {
            "bin_left_km": np.arange(0, max(8.0, math.ceil(audit["match_dist_km"].max())), 0.5),
        }
    )
    hist["bin_right_km"] = hist["bin_left_km"] + 0.5
    hist["count"] = [
        int(((audit["match_dist_km"] >= left) & (audit["match_dist_km"] < left + 0.5)).sum())
        for left in hist["bin_left_km"]
    ]
    hist.to_csv(SOURCE / "Match_distance_histogram_source.csv", index=False)
    return audit


def tidal_and_gssr_audits(primary: pd.DataFrame, rp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    tidal = pd.read_csv(SOURCE / "TableS_tidal_regime_metadata_source_tracked.csv")
    verified = tidal[tidal["source_status"].eq("source_verified")].copy()
    plotted = verified.merge(primary, on=["station_id", "station"], how="inner", validate="one_to_one")
    plotted = plotted.merge(rp[["station_id", "coast_rp_rp10_m"]], on="station_id", suffixes=("", "_recomputed"))
    plotted["plotted_count"] = len(plotted)
    plotted["coordinate_duplicate_count"] = plotted.groupby(["lat", "lon"])["station_id"].transform("size")
    if len(plotted) != 13:
        raise AssertionError(f"Expected 13 source-verified tidal stations in primary sample, found {len(plotted)}")
    plotted.to_csv(SOURCE / "FigS1_tidal_source_audit.csv", index=False)

    tide = plotted["spring_tidal_range_m"].to_numpy(float)
    water = plotted["coast_rp_rp10_m"].to_numpy(float)
    diagnostics: list[dict[str, object]] = [
        {
            "relationship": "storm_tide_vs_spring_tidal_range",
            "n_sites": len(plotted),
            "spearman": float(stats.spearmanr(water, tide).statistic),
            "partial_spearman_controlling_tidal_range": np.nan,
            "scope": "exploratory_source_verified_13_site_subset",
        }
    ]
    for metric in METRICS:
        terrain = plotted[metric].to_numpy(float)
        diagnostics.append(
            {
                "relationship": f"{metric}_vs_spring_tidal_range",
                "n_sites": len(plotted),
                "spearman": float(stats.spearmanr(terrain, tide).statistic),
                "partial_spearman_controlling_tidal_range": np.nan,
                "scope": "exploratory_source_verified_13_site_subset",
            }
        )
        diagnostics.append(
            {
                "relationship": f"storm_tide_vs_{metric}",
                "n_sites": len(plotted),
                "spearman": float(stats.spearmanr(water, terrain).statistic),
                "partial_spearman_controlling_tidal_range": float(
                    stats.pearsonr(
                        residualize(stats.rankdata(water), stats.rankdata(tide)),
                        residualize(stats.rankdata(terrain), stats.rankdata(tide)),
                    ).statistic
                ),
                "scope": "exploratory_source_verified_13_site_subset",
            }
        )
    diagnostic_frame = pd.DataFrame(diagnostics)
    diagnostic_frame.to_csv(SOURCE / "Tidal_covariation_diagnostics.csv", index=False)

    metadata = json.loads(GSSR_METADATA.read_text(encoding="utf-8"))
    fields = sorted({key for feature in metadata["features"] for key in feature.get("properties", {})})
    candidate = pd.read_csv(SOURCE / "Fig5_station_candidate_audit.csv")
    gssr_rows: list[dict[str, object]] = [
        {
            "audit_item": "available_metadata_fields",
            "value": ";".join(fields),
            "interpretation": "corrn is retained as the source metadata reconstruction correlation; no separate extreme-event skill field is present in the local metadata.",
        }
    ]
    for corr_threshold in (0.45, 0.55, 0.65):
        for years in (20, 25, 30):
            count = int((candidate["corrn"].ge(corr_threshold) & candidate["num_year"].ge(years)).sum())
            gssr_rows.append(
                {
                    "audit_item": f"eligible_corr_ge{corr_threshold:.2f}_years_ge{years}",
                    "value": count,
                    "interpretation": "Supporting GSSR-quality subset count only; this filter does not define the primary COAST-RP-terrain sample.",
                }
            )
    gssr_frame = pd.DataFrame(gssr_rows)
    gssr_frame.to_csv(SOURCE / "GSSR_metadata_field_audit.csv", index=False)
    return plotted, gssr_frame


def method_audit(primary: pd.DataFrame, rp_results: pd.DataFrame, match: pd.DataFrame) -> None:
    values = {
        "primary_station_count": len(primary),
        "primary_neighbour_rule": 4,
        "primary_window_width_km": 10,
        "primary_terrain_threshold_m_egm2008": 2,
        "primary_vertical_interpretation": "standardized EGM2008 terrain-elevation threshold; not an event-specific storm-tide water surface",
        "coast_return_periods_years": list(RETURN_PERIODS),
        "spatial_null": "10000 within-coastal-sector permutations",
        "moran_distance_thresholds_km": [150, 250],
        "included_match_distance_max_km": float(primary["match_dist_km"].max()),
        "excluded_match_count_gt6km": int((~match["included_in_primary_match_sample"]).sum()),
        "metric_identity": "connected_reference_land_pct = below_reference_land_pct * conditional_connectivity_pct / 100",
        "deltadtm_version_note": "v1.1.1 mask class 255 denotes clipping at 30 m EGM2008; the 2024 v1.0 paper describes a 10 m plus MSL support. Version-specific support is audited rather than conflated.",
        "rp10_primary_rows": int((rp_results["return_period_years"].eq(10)).sum()),
    }
    (SOURCE / "External_review_method_audit.json").write_text(json.dumps(values, indent=2), encoding="utf-8")


def main() -> int:
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    detail = pd.read_csv(SOURCE / "Terrain_robustness_grid_74stations.csv")
    required = {
        "window_area_km2",
        "reference_land_window_pct",
        "below_window_pct",
        "connected_window_pct",
    }
    missing = required - set(primary.columns)
    if missing:
        raise AssertionError(f"Rebuild the frozen primary analysis before diagnostics; missing columns: {sorted(missing)}")
    identity_error = np.nanmax(
        np.abs(
            primary["connected_reference_land_pct"]
            - primary["below_reference_land_pct"] * primary["conditional_connectivity_pct"] / 100.0
        )
    )
    if identity_error > 1e-7:
        raise AssertionError(f"Terrain metric decomposition failed: {identity_error}")

    rp = extract_return_periods(primary)
    rp_results, _ = return_period_diagnostics(primary, rp)
    jackknife_and_sectors(primary)
    spatial_autocorrelation(primary)
    denominator_diagnostics(primary)
    topology_diagnostics(primary, detail)
    match = match_audit()
    tidal_and_gssr_audits(primary, rp)
    method_audit(primary, rp_results, match)

    print("External-review diagnostics written.")
    print(
        rp_results[rp_results["return_period_years"].eq(10)][
            ["terrain_metric_label", "spearman", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p"]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

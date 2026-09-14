#!/usr/bin/env python3
"""Rebuild the frozen regional terrain and ranking analysis.

This is the authoritative post-review workflow. It uses DeltaDTM v1.1.1,
fixed physical windows and the official water mask. The former 15 m composite
denominator is retained only in legacy tables. Primary outputs separate:

* below-threshold land share (lowland prevalence);
* conditional connectivity among below-threshold land;
* connected below-threshold share of reference land; and
* connected area; and
* represented-land coverage of the nominal station window.

The script also evaluates window, threshold, neighbourhood, marine-seed,
vertical-offset and COAST-RP matching sensitivities for the full regional
sample, then applies one consistent six-sector spatial inference scheme.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from add_advanced_terrain_rank_diagnostics import (  # noqa: E402
    cell_area_km2,
    fixed_km_bbox,
    read_dem_window_fast,
    sum_area,
)
from add_mask_aware_terrain_diagnostics import (  # noqa: E402
    MASK_OUTSIDE_SUPPORT,
    coastal_sector,
    resolve_marine_seed,
)
from inundation_sensitivity import valid_mask  # noqa: E402


FIG_SOURCE = ROOT / "data" / "figure_source"
INPUT_METRICS = FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv"
CANDIDATE_AUDIT = FIG_SOURCE / "Fig5_station_candidate_audit.csv"

WIDTHS_KM = (5.0, 10.0, 20.0)
LEVELS_M = (1.0, 2.0, 3.0)
NEIGHBOURS = (4, 8)
SEED_RULES = ("official_adaptive", "local_ocean_only")
VERTICAL_OFFSETS_M = (-1.0, -0.5, 0.5, 1.0)
PRIMARY_MAX_MATCH_KM = 6.0
PERMUTATIONS = 10_000
BLOCK_BOOTSTRAPS = 2_000

STRUCTURES = {
    4: ndi.generate_binary_structure(2, 1),
    8: np.ones((3, 3), dtype=bool),
}


def classify(
    elev: np.ndarray,
    valid: np.ndarray,
    mask: np.ndarray,
    area: np.ndarray,
    tidal_water: np.ndarray,
    eta_m: float,
    neighbours: int,
    elevation_offset_m: float = 0.0,
) -> dict[str, float | int]:
    """Return decomposed terrain metrics for one explicit configuration."""
    land = mask == 0
    # Class 255 is clipped product support, not a finite terrain observation.
    # It remains visible in the audit counts but never enters an areal
    # denominator or a below-threshold layer.
    reference_land = valid & land
    effective_elev = elev + elevation_offset_m
    below = valid & land & np.isfinite(effective_elev) & (effective_elev <= eta_m)
    passable = below | tidal_water
    connected = ndi.binary_propagation(
        tidal_water,
        structure=STRUCTURES[neighbours],
        mask=passable,
    ) & below

    reference_land_area = sum_area(area, reference_land)
    window_area = sum_area(area, np.isfinite(area))
    below_area = sum_area(area, below)
    connected_area = sum_area(area, connected)
    return {
        "window_area_km2": window_area,
        "reference_land_area_km2": reference_land_area,
        "below_area_km2": below_area,
        "connected_area_km2": connected_area,
        "unconnected_below_area_km2": max(below_area - connected_area, 0.0),
        "below_reference_land_pct": (
            100.0 * below_area / reference_land_area if reference_land_area else np.nan
        ),
        "conditional_connectivity_pct": (
            100.0 * connected_area / below_area if below_area else np.nan
        ),
        "connected_reference_land_pct": (
            100.0 * connected_area / reference_land_area if reference_land_area else np.nan
        ),
        "reference_land_window_pct": (
            100.0 * reference_land_area / window_area if window_area else np.nan
        ),
        "below_window_pct": 100.0 * below_area / window_area if window_area else np.nan,
        "connected_window_pct": 100.0 * connected_area / window_area if window_area else np.nan,
        "below_cells": int(below.sum()),
        "connected_cells": int(connected.sum()),
    }


def local_ocean_seed(mask: np.ndarray) -> tuple[np.ndarray, bool]:
    """Strict sensitivity seed: only class-1 ocean inside the analysis crop."""
    ocean = mask == 1
    return ocean, bool(ocean.any())


def station_configurations(row: pd.Series) -> list[dict[str, object]]:
    """Compute all one-station configurations without legacy denominators."""
    results: list[dict[str, object]] = []
    for width_km in WIDTHS_KM:
        bbox = fixed_km_bbox(float(row["lon"]), float(row["lat"]), width_km)
        lon2d, lat2d, elev, dem_source, dem_meta, dem_tiles = read_dem_window_fast(bbox)
        valid = valid_mask(elev)
        mask, adaptive_tidal, seed_audit = resolve_marine_seed(
            float(row["lon"]),
            float(row["lat"]),
            bbox,
            elev.shape,
            dem_meta["transform"],
            dem_meta["crs"],
        )
        area = cell_area_km2(lon2d, lat2d)
        strict_tidal, strict_resolved = local_ocean_seed(mask)
        seeds = {
            "official_adaptive": (
                adaptive_tidal,
                str(seed_audit["marine_seed_status"]).startswith("resolved_"),
                str(seed_audit["marine_seed_status"]),
            ),
            "local_ocean_only": (
                strict_tidal,
                strict_resolved,
                "resolved_local_ocean_only" if strict_resolved else "unresolved_no_local_ocean",
            ),
        }

        common = {
            "station_id": row["station_id"],
            "station": row["station"],
            "lat": row["lat"],
            "lon": row["lon"],
            "coast_rp_rp10_m": row["coast_rp_rp10_m"],
            "match_dist_km": row["match_dist_km"],
            "window_width_km": width_km,
            "terrain_source": dem_source,
            "terrain_tiles": ";".join(dem_tiles),
            "mask_outside_support_cells": int((mask == MASK_OUTSIDE_SUPPORT).sum()),
            "official_clipped_255_cells": int((mask == 255).sum()),
            "coastal_sector": coastal_sector(row),
        }
        for eta_m in LEVELS_M:
            for neighbours in NEIGHBOURS:
                for seed_rule in SEED_RULES:
                    tidal_water, seed_resolved, seed_status = seeds[seed_rule]
                    record = {
                        **common,
                        "eta_m": eta_m,
                        "neighbours": neighbours,
                        "seed_rule": seed_rule,
                        "seed_resolved": seed_resolved,
                        "seed_status": seed_status,
                        "elevation_offset_m": 0.0,
                    }
                    if seed_resolved:
                        record.update(
                            classify(
                                elev,
                                valid,
                                mask,
                                area,
                                tidal_water,
                                eta_m,
                                neighbours,
                            )
                        )
                    results.append(record)

        if width_km == 10.0:
            for offset_m in VERTICAL_OFFSETS_M:
                record = {
                    **common,
                    "eta_m": 2.0,
                    "neighbours": 4,
                    "seed_rule": "official_adaptive",
                    "seed_resolved": seeds["official_adaptive"][1],
                    "seed_status": seeds["official_adaptive"][2],
                    "elevation_offset_m": offset_m,
                }
                if bool(record["seed_resolved"]):
                    record.update(
                        classify(
                            elev,
                            valid,
                            mask,
                            area,
                            adaptive_tidal,
                            2.0,
                            4,
                            elevation_offset_m=offset_m,
                        )
                    )
                results.append(record)
    return results


def rank_summary(
    frame: pd.DataFrame,
    metric: str,
    setting: str,
    seed: int,
) -> dict[str, object]:
    work = frame.dropna(subset=["coast_rp_rp10_m", metric]).copy()
    n = len(work)
    if n < 8:
        return {"setting": setting, "terrain_metric": metric, "n_sites": n}
    water = work["coast_rp_rp10_m"].to_numpy(float)
    terrain = work[metric].to_numpy(float)
    observed_s = float(stats.spearmanr(water, terrain).statistic)
    observed_k = float(stats.kendalltau(water, terrain).statistic)
    # Spearman correlation is Pearson correlation of ranks. Generate the
    # station-label null in vectorized batches so the 10,000-permutation audit
    # remains practical across the full sensitivity grid.
    water_rank = stats.rankdata(water).astype(float)
    terrain_rank = stats.rankdata(terrain).astype(float)
    water_rank -= water_rank.mean()
    terrain_rank -= terrain_rank.mean()
    denominator = float(np.linalg.norm(water_rank) * np.linalg.norm(terrain_rank))
    rng = np.random.default_rng(seed)
    null_s = np.empty(PERMUTATIONS, dtype=float)
    batch_size = 1_000
    for start in range(0, PERMUTATIONS, batch_size):
        stop = min(start + batch_size, PERMUTATIONS)
        permuted = np.stack([rng.permutation(terrain_rank) for _ in range(stop - start)])
        null_s[start:stop] = permuted @ water_rank / denominator
    p_two = float((np.sum(np.abs(null_s) >= abs(observed_s)) + 1) / (PERMUTATIONS + 1))
    k = max(1, math.ceil(0.2 * n))
    top_water = set(work.nlargest(k, "coast_rp_rp10_m")["station_id"])
    top_terrain = set(work.nlargest(k, metric)["station_id"])
    overlap = len(top_water & top_terrain)
    return {
        "setting": setting,
        "terrain_metric": metric,
        "n_sites": n,
        "spearman": observed_s,
        "kendall": observed_k,
        "permutation_two_sided_p": p_two,
        "top_n": k,
        "top_overlap": overlap,
        "top_overlap_expected_independent": k * k / n,
        "top_mismatch_fraction": 1.0 - overlap / k,
        "top_water_sites": ";".join(sorted(top_water)),
        "top_terrain_sites": ";".join(sorted(top_terrain)),
    }


def sector_block_interval(
    frame: pd.DataFrame,
    metric: str,
    setting: str,
    seed: int,
) -> dict[str, object]:
    work = frame.dropna(subset=["coast_rp_rp10_m", metric, "coastal_sector"]).copy()
    sectors = sorted(work["coastal_sector"].unique())
    groups = {s: work[work["coastal_sector"].eq(s)].copy() for s in sectors}
    rng = np.random.default_rng(seed)
    values = np.full(BLOCK_BOOTSTRAPS, np.nan, dtype=float)
    for i in range(BLOCK_BOOTSTRAPS):
        sampled = rng.choice(sectors, size=len(sectors), replace=True)
        boot = pd.concat([groups[s] for s in sampled], ignore_index=True)
        if boot[metric].nunique() > 1 and boot["coast_rp_rp10_m"].nunique() > 1:
            values[i] = float(boot["coast_rp_rp10_m"].corr(boot[metric], method="spearman"))
    return {
        "setting": setting,
        "terrain_metric": metric,
        "n_sites": len(work),
        "n_sectors": len(sectors),
        "sectors": ";".join(sectors),
        "spearman_observed": float(work["coast_rp_rp10_m"].corr(work[metric], method="spearman")),
        "spearman_sector_bootstrap_p025": float(np.nanpercentile(values, 2.5)),
        "spearman_sector_bootstrap_p500": float(np.nanpercentile(values, 50.0)),
        "spearman_sector_bootstrap_p975": float(np.nanpercentile(values, 97.5)),
        "n_bootstrap": BLOCK_BOOTSTRAPS,
    }


def choose_configuration(
    detail: pd.DataFrame,
    *,
    width_km: float = 10.0,
    eta_m: float = 2.0,
    neighbours: int = 4,
    seed_rule: str = "official_adaptive",
    elevation_offset_m: float = 0.0,
    max_match_km: float | None = PRIMARY_MAX_MATCH_KM,
) -> pd.DataFrame:
    out = detail[
        detail["window_width_km"].eq(width_km)
        & detail["eta_m"].eq(eta_m)
        & detail["neighbours"].eq(neighbours)
        & detail["seed_rule"].eq(seed_rule)
        & detail["elevation_offset_m"].eq(elevation_offset_m)
        & detail["seed_resolved"].eq(True)
    ].copy()
    if max_match_km is not None:
        out = out[out["match_dist_km"].le(max_match_km)].copy()
    return out


def one_at_a_time_settings(detail: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    configs = [("primary:10km,2m,4n,adaptive,match<=6km", choose_configuration(detail))]
    for width in (5.0, 20.0):
        configs.append((f"window:{width:g}km", choose_configuration(detail, width_km=width)))
    for eta in (1.0, 3.0):
        configs.append((f"threshold:{eta:g}m", choose_configuration(detail, eta_m=eta)))
    configs.append(("neighbours:8", choose_configuration(detail, neighbours=8)))
    configs.append(("seed:local-ocean-only", choose_configuration(detail, seed_rule="local_ocean_only")))
    for offset in VERTICAL_OFFSETS_M:
        configs.append((f"uniform-elevation-offset:{offset:+g}m", choose_configuration(detail, elevation_offset_m=offset)))
    configs.append(("COAST-match:<=1km", choose_configuration(detail, max_match_km=1.0)))
    configs.append(("COAST-match:<=2km", choose_configuration(detail, max_match_km=2.0)))
    configs.append(("COAST-match:distance-unrestricted", choose_configuration(detail, max_match_km=None)))
    return configs


def rank_stability(
    baseline: pd.DataFrame,
    sensitivity: pd.DataFrame,
    metric: str,
) -> dict[str, float | int]:
    """Compare terrain order and top-set membership with the primary setting."""
    common = baseline[["station_id", metric]].merge(
        sensitivity[["station_id", metric]],
        on="station_id",
        suffixes=("_baseline", "_sensitivity"),
    ).dropna()
    n = len(common)
    if n < 3:
        return {
            "rank_stability_n": n,
            "terrain_rank_spearman_vs_primary": np.nan,
            "top20_jaccard_vs_primary": np.nan,
            "top20_membership_changes_vs_primary": np.nan,
        }
    base_col = f"{metric}_baseline"
    sensitivity_col = f"{metric}_sensitivity"
    k = max(1, math.ceil(0.2 * n))
    base_top = set(common.nlargest(k, base_col)["station_id"])
    sensitivity_top = set(common.nlargest(k, sensitivity_col)["station_id"])
    return {
        "rank_stability_n": n,
        "terrain_rank_spearman_vs_primary": float(
            common[base_col].corr(common[sensitivity_col], method="spearman")
        ),
        "top20_jaccard_vs_primary": (
            len(base_top & sensitivity_top) / len(base_top | sensitivity_top)
            if (base_top | sensitivity_top)
            else np.nan
        ),
        "top20_membership_changes_vs_primary": len(base_top ^ sensitivity_top),
    }


def topk_null_curve(frame: pd.DataFrame, metric: str, seed: int) -> pd.DataFrame:
    work = frame.dropna(subset=["coast_rp_rp10_m", metric]).copy()
    n = len(work)
    water_order = work.sort_values("coast_rp_rp10_m", ascending=False)["station_id"].tolist()
    terrain_order = work.sort_values(metric, ascending=False)["station_id"].tolist()
    rows = []
    for share in np.arange(0.10, 0.45, 0.05):
        k = max(1, math.ceil(share * n))
        observed = len(set(water_order[:k]) & set(terrain_order[:k]))
        # Under station-label permutation, top-k overlap is exactly
        # hypergeometric: population n, k water-top sites, k random draws.
        null_dist = stats.hypergeom(M=n, n=k, N=k)
        rows.append(
            {
                "terrain_metric": metric,
                "top_share": share,
                "n_sites": n,
                "top_n": k,
                "observed_overlap": observed,
                "null_median": float(null_dist.ppf(0.5)),
                "null_p025": float(null_dist.ppf(0.025)),
                "null_p975": float(null_dist.ppf(0.975)),
                "low_tail_p": float(null_dist.cdf(observed)),
                "null_method": "exact hypergeometric station-label permutation equivalent",
            }
        )
    return pd.DataFrame(rows)


def leave_one_sector(frame: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    sectors = sorted(frame["coastal_sector"].unique())
    for metric in metrics:
        for omitted in sectors:
            work = frame[~frame["coastal_sector"].eq(omitted)].copy()
            row = rank_summary(work, metric, f"omit-sector:{omitted}", 20260850 + len(rows))
            row["omitted_sector"] = omitted
            row["omitted_n"] = int(frame["coastal_sector"].eq(omitted).sum())
            rows.append(row)
    return pd.DataFrame(rows)


def sample_flow(input_rows: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    audit = pd.read_csv(CANDIDATE_AUDIT)
    primary = choose_configuration(detail)
    return pd.DataFrame(
        [
            {"stage": "GSSR metadata stations inside geographic bounds", "n": len(audit)},
            {"stage": "DeltaDTM v1.1 elevation tiles available", "n": int(audit["deltadtm_tile_available"].eq(True).sum())},
            {"stage": "Official marine seed resolved in 10 km window/context", "n": int(input_rows["marine_seed_resolved"].eq(True).sum())},
            {"stage": "COAST-RP nearest match within 6 km (primary)", "n": len(primary)},
            {"stage": "GSSR record >=25 years and reconstruction correlation >=0.55", "n": int((primary["station_id"].isin(audit[audit["passes_years_ge25"].eq(True) & audit["passes_corr_ge055"].eq(True)]["station_id"])).sum())},
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reuse-detail",
        action="store_true",
        help="Reuse Terrain_robustness_grid_74stations.csv and rebuild only summaries.",
    )
    args = parser.parse_args()
    source = pd.read_csv(INPUT_METRICS)
    detail_path = FIG_SOURCE / "Terrain_robustness_grid_74stations.csv"
    if args.reuse_detail:
        if not detail_path.exists():
            raise FileNotFoundError(f"Cannot reuse missing detail table: {detail_path}")
        detail = pd.read_csv(detail_path)
    else:
        rows: list[dict[str, object]] = []
        for i, (_, station) in enumerate(source.iterrows(), start=1):
            print(f"[{i}/{len(source)}] frozen terrain grid {station['station_id']}", flush=True)
            rows.extend(station_configurations(station))
        detail = pd.DataFrame(rows)
        detail.to_csv(detail_path, index=False)

    primary = choose_configuration(detail)
    primary.to_csv(FIG_SOURCE / "Primary_terrain_components_68stations.csv", index=False)
    metrics = [
        "connected_reference_land_pct",
        "below_reference_land_pct",
        "conditional_connectivity_pct",
        "connected_area_km2",
    ]

    rank_rows = []
    block_rows = []
    baseline = choose_configuration(detail)
    for setting_index, (setting, frame) in enumerate(one_at_a_time_settings(detail)):
        for metric_index, metric in enumerate(metrics):
            seed = 20260824 + 100 * setting_index + metric_index
            summary = rank_summary(frame, metric, setting, seed)
            summary.update(rank_stability(baseline, frame, metric))
            rank_rows.append(summary)
            if setting.startswith("primary:"):
                block_rows.append(sector_block_interval(frame, metric, setting, seed + 50_000))
    pd.DataFrame(rank_rows).to_csv(FIG_SOURCE / "Rank_robustness_one_at_a_time.csv", index=False)
    pd.DataFrame(block_rows).to_csv(FIG_SOURCE / "Spatial_sector_bootstrap_intervals.csv", index=False)

    curves = [topk_null_curve(primary, metric, 20260924 + i) for i, metric in enumerate(metrics)]
    pd.concat(curves, ignore_index=True).to_csv(FIG_SOURCE / "Topk_overlap_null_curves.csv", index=False)
    leave_one_sector(primary, metrics).to_csv(FIG_SOURCE / "Leave_one_coastal_sector_out.csv", index=False)

    sectors = primary[["station_id", "station", "lat", "lon", "coastal_sector"]].copy()
    sectors.to_csv(FIG_SOURCE / "Primary_station_coastal_sectors.csv", index=False)
    sample_flow(source, detail).to_csv(FIG_SOURCE / "Primary_sample_flow.csv", index=False)

    product_audit = pd.DataFrame(
        [
            {
                "product": "DeltaDTM",
                "release": "v1.1.1",
                "tile_tag": "DeltaDTM v1.1.1 / DeltaDTM.jl v1.1.1",
                "vertical_reference": "EGM2008",
                "release_cap_m": 30.0,
                "paper_v1_0_cap_m": 10.0,
                "mask_outside_support_fill": int(MASK_OUTSIDE_SUPPORT),
                "official_255_cells_in_primary_analysis_windows": int(primary["official_clipped_255_cells"].sum()),
                "outside_support_cells_in_primary_analysis_windows": int(primary["mask_outside_support_cells"].sum()),
                "note": "The 2024 paper documents v1.0; the downloaded v1.1 README documents the 30 m EGM2008 cap. Outside-support fill is kept distinct from class 255 and excluded from all land denominators.",
            }
        ]
    )
    product_audit.to_csv(FIG_SOURCE / "DeltaDTM_v1_1_product_version_audit.csv", index=False)

    print("\nPrimary decomposed associations")
    print(
        pd.DataFrame(rank_rows)
        .query("setting == 'primary:10km,2m,4n,adaptive,match<=6km'")
        [["terrain_metric", "n_sites", "spearman", "kendall", "permutation_two_sided_p", "top_overlap", "top_n"]]
        .to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Add final submission-polish diagnostics for the CEE manuscript.

This script adds statistical checks that sit between the existing source
tables and the final manuscript narrative:

1. Permutation null distributions for rank-discordance metrics.
2. Leave-one-country/coastal-sector-out sensitivity.
3. D10 ranking under GSSR prediction-interval lower/upper envelopes.
4. COAST-RP total/ETC/TC component checks for the NW Europe subset.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
FIG_SOURCE = ROOT / "data" / "figure_source"
COAST_DIR = ROOT / "data" / "raw" / "coast_rp" / "extracted"


def top_set_stats(frame: pd.DataFrame, water_col: str, terrain_col: str) -> dict[str, object]:
    ok = frame.dropna(subset=[water_col, terrain_col]).copy()
    ok["water_rank"] = ok[water_col].rank(ascending=False, method="min")
    ok["terrain_rank"] = ok[terrain_col].rank(ascending=False, method="min")
    top_n = max(1, math.ceil(0.2 * len(ok)))
    top_water = set(ok.nsmallest(top_n, "water_rank")["station_id"])
    top_terrain = set(ok.nsmallest(top_n, "terrain_rank")["station_id"])
    overlap = len(top_water & top_terrain)
    return {
        "n_sites": int(len(ok)),
        "top_n": int(top_n),
        "spearman": float(ok[water_col].corr(ok[terrain_col], method="spearman")),
        "kendall": float(ok[water_col].corr(ok[terrain_col], method="kendall")),
        "top_overlap": int(overlap),
        "top_mismatch_fraction": float(1.0 - overlap / top_n),
        "top_water_sites": ";".join(sorted(top_water)),
        "top_terrain_sites": ";".join(sorted(top_terrain)),
    }


def permutation_summary(
    frame: pd.DataFrame,
    label: str,
    water_col: str = "coast_rp_rp10_m",
    terrain_col: str = "connected_2m_lowland_pct",
    n_perm: int = 10_000,
    seed: int = 20260701,
) -> dict[str, object]:
    ok = frame.dropna(subset=[water_col, terrain_col]).copy().reset_index(drop=True)
    observed = top_set_stats(ok, water_col, terrain_col)
    water = ok[water_col].to_numpy(dtype=float)
    terrain = ok[terrain_col].to_numpy(dtype=float)
    water_rank = stats.rankdata(-water, method="average")
    terrain_rank = stats.rankdata(-terrain, method="average")
    top_n = int(observed["top_n"])
    top_water = set(np.argsort(water_rank)[:top_n].tolist())
    water_rank_centered = water_rank - water_rank.mean()
    water_rank_norm = float(np.sqrt(np.sum(water_rank_centered**2)))
    water_sign = np.sign(water_rank[:, None] - water_rank[None, :])
    tri = np.triu_indices(len(water_rank), k=1)
    water_pair_sign = water_sign[tri]
    pair_denominator = float(np.sum(water_pair_sign != 0))
    rng = np.random.default_rng(seed)
    spearman_null = np.empty(n_perm, dtype=float)
    kendall_null = np.empty(n_perm, dtype=float)
    overlap_null = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        permuted_rank = terrain_rank[rng.permutation(len(terrain_rank))]
        pr_centered = permuted_rank - permuted_rank.mean()
        spearman_null[i] = float(np.sum(water_rank_centered * pr_centered) / (water_rank_norm * np.sqrt(np.sum(pr_centered**2))))
        terrain_pair_sign = np.sign(permuted_rank[:, None] - permuted_rank[None, :])[tri]
        kendall_null[i] = float(np.sum(water_pair_sign * terrain_pair_sign) / pair_denominator)
        top_terrain = set(np.argsort(permuted_rank)[:top_n].tolist())
        overlap_null[i] = len(top_water & top_terrain)
    return {
        "sample": label,
        **observed,
        "n_permutations": n_perm,
        "spearman_null_p025": float(np.nanpercentile(spearman_null, 2.5)),
        "spearman_null_p500": float(np.nanpercentile(spearman_null, 50.0)),
        "spearman_null_p975": float(np.nanpercentile(spearman_null, 97.5)),
        "kendall_null_p025": float(np.nanpercentile(kendall_null, 2.5)),
        "kendall_null_p500": float(np.nanpercentile(kendall_null, 50.0)),
        "kendall_null_p975": float(np.nanpercentile(kendall_null, 97.5)),
        "overlap_null_p025": float(np.nanpercentile(overlap_null, 2.5)),
        "overlap_null_p500": float(np.nanpercentile(overlap_null, 50.0)),
        "overlap_null_p975": float(np.nanpercentile(overlap_null, 97.5)),
        "spearman_left_p": float((np.sum(spearman_null <= observed["spearman"]) + 1) / (n_perm + 1)),
        "kendall_left_p": float((np.sum(kendall_null <= observed["kendall"]) + 1) / (n_perm + 1)),
        "overlap_low_p": float((np.sum(overlap_null <= observed["top_overlap"]) + 1) / (n_perm + 1)),
    }


def sector_for_station(row: pd.Series) -> str:
    sid = str(row["station_id"]).lower()
    station = str(row.get("station", "")).lower()
    if "-uk" in sid or sid in {"sheerness-p015-uk", "newlyn-p001-uk"}:
        return "United Kingdom"
    if "-nl" in sid or "hoek" in sid or "denhelder" in sid or "delfzijl" in sid:
        return "Netherlands"
    if "germany" in sid or "cuxhaven" in sid:
        return "Germany"
    if "denmark" in sid or "esbjerg" in sid:
        return "Denmark"
    if "norway" in sid or "tregde" in sid:
        return "Norway"
    if any(token in sid for token in ["brest", "le-", "port-", "saint-", "cherbourg", "dieppe", "dunkerque", "boulogne", "roscoff"]):
        return "France"
    if any(token in station for token in ["france", "havre", "dieppe", "dunkerque", "boulogne", "roscoff", "cherbourg"]):
        return "France"
    return "Other"


def leave_one_sector(frame: pd.DataFrame, sample_label: str) -> pd.DataFrame:
    work = frame.copy()
    work["sector"] = work.apply(sector_for_station, axis=1)
    rows = []
    rows.append({"sample": sample_label, "omitted_sector": "none", **top_set_stats(work, "coast_rp_rp10_m", "connected_2m_lowland_pct")})
    for sector in sorted(work["sector"].dropna().unique()):
        sub = work[work["sector"].ne(sector)].copy()
        if len(sub.dropna(subset=["coast_rp_rp10_m", "connected_2m_lowland_pct"])) < 10:
            continue
        stats = top_set_stats(sub, "coast_rp_rp10_m", "connected_2m_lowland_pct")
        rows.append({"sample": sample_label, "omitted_sector": sector, **stats})
    return pd.DataFrame(rows)


def candidate_pool_frames() -> dict[str, pd.DataFrame]:
    pool = pd.read_csv(FIG_SOURCE / "Fig5_candidate_pool_terrain_screening.csv")
    out = {}
    for threshold in [0.45, 0.55, 0.65]:
        out[f"eligible corr>={threshold:.2f}"] = pool[pool["corrn"].ge(threshold)].copy()
    return out


def build_permutation_tables() -> None:
    base = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    rows = [permutation_summary(base, "baseline 30-station subset", seed=20260701)]
    for i, (label, frame) in enumerate(candidate_pool_frames().items(), start=1):
        rows.append(permutation_summary(frame, label, seed=20260701 + i))
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig5_rank_permutation_null_summary.csv", index=False)


def build_leave_sector_tables() -> None:
    base = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    tables = [leave_one_sector(base, "baseline 30-station subset")]
    pool = pd.read_csv(FIG_SOURCE / "Fig5_candidate_pool_terrain_screening.csv")
    tables.append(leave_one_sector(pool[pool["corrn"].ge(0.55)].copy(), "eligible corr>=0.55 candidate pool"))
    out = pd.concat(tables, ignore_index=True)
    out.to_csv(FIG_SOURCE / "Fig5_leave_one_sector_sensitivity.csv", index=False)


def build_prediction_bound_d10_tables() -> None:
    ext = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening_with_uncertainty.csv")
    rows = []
    for _, row in ext.iterrows():
        nominal = float(row["coast_rp_rp10_m"] - row["gssr_rp10_m"])
        lower = row.get("gssr_predint_rp10_lower_m", np.nan)
        upper = row.get("gssr_predint_rp10_upper_m", np.nan)
        rows.append(
            {
                "station_id": row["station_id"],
                "station": row["station"],
                "coast_rp_rp10_m": row["coast_rp_rp10_m"],
                "gssr_rp10_m": row["gssr_rp10_m"],
                "gssr_predint_rp10_lower_m": lower,
                "gssr_predint_rp10_upper_m": upper,
                "D10_nominal_m": nominal,
                "D10_with_gssr_lower_m": float(row["coast_rp_rp10_m"] - lower) if np.isfinite(lower) else np.nan,
                "D10_with_gssr_upper_m": float(row["coast_rp_rp10_m"] - upper) if np.isfinite(upper) else np.nan,
                "connected_2m_lowland_pct": row["connected_2m_lowland_pct"],
            }
        )
    out = pd.DataFrame(rows)
    for col in ["D10_nominal_m", "D10_with_gssr_lower_m", "D10_with_gssr_upper_m"]:
        out[col.replace("_m", "_rank")] = out[col].rank(ascending=False, method="min")
    out.to_csv(FIG_SOURCE / "Fig5_D10_prediction_interval_scenarios.csv", index=False)

    summary_rows = []
    for scenario, col in [
        ("nominal GSSR RP10", "D10_nominal_m"),
        ("GSSR lower prediction-bound RP10", "D10_with_gssr_lower_m"),
        ("GSSR upper prediction-bound RP10", "D10_with_gssr_upper_m"),
    ]:
        ranked = out.dropna(subset=[col]).sort_values(col, ascending=False).head(6)
        summary_rows.append(
            {
                "scenario": scenario,
                "top6_D10_sites": ";".join(ranked["station"].astype(str)),
                "top3_D10_sites": ";".join(ranked.head(3)["station"].astype(str)),
                "contains_sheerness": bool(ranked["station_id"].eq("sheerness-p015-uk").any()),
                "contains_brest": bool(ranked["station_id"].isin(["brest", "brest-france"]).any()),
                "contains_newlyn": bool(ranked["station_id"].eq("newlyn-p001-uk").any()),
            }
        )
    pd.DataFrame(summary_rows).to_csv(FIG_SOURCE / "Fig5_D10_prediction_interval_scenario_summary.csv", index=False)


def nearest_component_value(ds: xr.Dataset, lon0: float, lat0: float, var: str = "storm_tide_rp_0010") -> tuple[float, float]:
    lon = ds["station_x_coordinate"].values.astype(float)
    lat = ds["station_y_coordinate"].values.astype(float)
    values = ds[var].values.astype(float)
    # Haversine is unnecessary for nearest-neighbour ordering within these small
    # distances; equirectangular scaling keeps longitude convergence reasonable.
    scale = math.cos(math.radians(float(lat0)))
    dist2 = ((lon - lon0) * scale) ** 2 + (lat - lat0) ** 2
    idx = int(np.nanargmin(dist2))
    km = float(math.sqrt(dist2[idx]) * 111.32)
    return float(values[idx]), km


def build_coastrp_component_tables() -> None:
    ext = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    etc = xr.open_dataset(COAST_DIR / "COAST-RP_ETC.nc")
    tc = xr.open_dataset(COAST_DIR / "COAST-RP_TC.nc")
    rows = []
    for _, row in ext.iterrows():
        etc_val, etc_dist = nearest_component_value(etc, float(row["lon"]), float(row["lat"]))
        tc_val, tc_dist = nearest_component_value(tc, float(row["lon"]), float(row["lat"]))
        total = float(row["coast_rp_rp10_m"])
        rows.append(
            {
                "station_id": row["station_id"],
                "station": row["station"],
                "coast_rp_total_rp10_m": total,
                "coast_rp_etc_rp10_m": etc_val,
                "coast_rp_tc_rp10_m": tc_val,
                "etc_match_dist_km": etc_dist,
                "tc_match_dist_km": tc_dist,
                "etc_to_total_ratio": etc_val / total if total else np.nan,
                "tc_to_total_ratio": tc_val / total if total else np.nan,
                "tc_minus_etc_m": tc_val - etc_val,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig5_coastrp_component_context.csv", index=False)
    summary = pd.DataFrame(
        [
            {
                "n_sites": len(out),
                "median_etc_to_total_ratio": float(out["etc_to_total_ratio"].median()),
                "min_etc_to_total_ratio": float(out["etc_to_total_ratio"].min()),
                "median_tc_to_total_ratio": float(out["tc_to_total_ratio"].median()),
                "max_tc_to_total_ratio": float(out["tc_to_total_ratio"].max()),
                "stations_with_tc_exceeding_etc": int((out["tc_minus_etc_m"] > 0).sum()),
                "median_etc_match_dist_km": float(out["etc_match_dist_km"].median()),
                "median_tc_match_dist_km": float(out["tc_match_dist_km"].median()),
            }
        ]
    )
    summary.to_csv(FIG_SOURCE / "Fig5_coastrp_component_context_summary.csv", index=False)


def main() -> int:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    build_permutation_tables()
    build_leave_sector_tables()
    build_prediction_bound_d10_tables()
    build_coastrp_component_tables()
    print("Wrote final submission-polish diagnostics")
    print(pd.read_csv(FIG_SOURCE / "Fig5_rank_permutation_null_summary.csv")[
        ["sample", "n_sites", "spearman", "spearman_left_p", "top_overlap", "top_n", "overlap_low_p"]
    ].to_string(index=False))
    print(pd.read_csv(FIG_SOURCE / "Fig5_leave_one_sector_sensitivity.csv")[
        ["sample", "omitted_sector", "n_sites", "spearman", "top_overlap", "top_n", "top_mismatch_fraction"]
    ].to_string(index=False))
    print(pd.read_csv(FIG_SOURCE / "Fig5_coastrp_component_context_summary.csv").to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

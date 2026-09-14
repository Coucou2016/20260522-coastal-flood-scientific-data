#!/usr/bin/env python3
"""Merge GSSR daily surge with COAST-RP return periods per station."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from combo1_utils import CONFIG, PROCESSED, ensure_dirs, load_config, read_gssr_station, save_json

MATCH_PATH = PROCESSED / "coast_rp_nearest.parquet"


def gssr_empirical_rp(gssr: pd.DataFrame, rp_years: list[int]) -> dict[int, float]:
    """Interpolate annual maxima on Weibull positions without extrapolation."""
    annual = gssr.groupby(gssr["date"].dt.year)["surge_m"].max().dropna()
    if len(annual) < 5:
        return {rp: float(np.nan) for rp in rp_years}
    ranked = np.sort(annual.to_numpy(dtype=float))
    n = len(ranked)
    nonexceedance = np.arange(1, n + 1, dtype=float) / (n + 1.0)
    out = {}
    for rp in rp_years:
        target = 1.0 - 1.0 / float(rp)
        if target < nonexceedance[0] or target > nonexceedance[-1]:
            out[rp] = float(np.nan)
        else:
            out[rp] = float(np.interp(target, nonexceedance, ranked))
    return out


def merge_all(config_path: Path = CONFIG, match_path: Path = MATCH_PATH) -> pd.DataFrame:
    cfg = load_config(config_path)
    match_df = pd.read_parquet(match_path)
    frames = []
    summary_rows = []

    for st in cfg["stations"]:
        gssr = read_gssr_station(st)
        gssr["date"] = pd.to_datetime(gssr["date"])
        row_match = match_df[match_df["station_id"] == st["id"]].iloc[0]

        emp = gssr_empirical_rp(gssr, [10, 50, 100])
        n_annual = int(gssr.groupby(gssr["date"].dt.year)["surge_m"].max().dropna().size)
        summary_rows.append(
            {
                "station_id": st["id"],
                "gssr_rp10_m": emp[10],
                "gssr_rp50_m": emp[50],
                "gssr_rp100_m": emp[100],
                "gssr_empirical_method": "annual-maxima Weibull plotting positions with linear interpolation and no extrapolation",
                "gssr_n_annual_maxima": n_annual,
                "gssr_empirical_max_supported_rp_years": n_annual + 1,
                "coast_rp_rp10_m": row_match["coast_rp_rp10_m"],
                "coast_rp_rp50_m": row_match["coast_rp_rp50_m"],
                "coast_rp_rp100_m": row_match["coast_rp_rp100_m"],
                "match_dist_km": row_match["match_dist_km"],
                "match_flag": row_match.get("match_flag", "ok"),
                "gssr_max_m": float(gssr["surge_m"].max()),
                "gssr_p99_m": float(gssr["surge_m"].quantile(0.99)),
            }
        )

        gssr = gssr.assign(
            coast_rp_rp10_m=row_match["coast_rp_rp10_m"],
            coast_rp_rp100_m=row_match["coast_rp_rp100_m"],
            match_dist_km=row_match["match_dist_km"],
        )
        frames.append(gssr)

    merged = pd.concat(frames, ignore_index=True)
    rp_compare = pd.DataFrame(summary_rows)
    rp_compare["rp10_bias_m"] = rp_compare["gssr_rp10_m"] - rp_compare["coast_rp_rp10_m"]
    rp_compare["rp100_bias_m"] = rp_compare["gssr_rp100_m"] - rp_compare["coast_rp_rp100_m"]
    valid = rp_compare.dropna(subset=["gssr_rp10_m", "coast_rp_rp10_m"])
    if len(valid) >= 3:
        r10 = stats.pearsonr(valid["gssr_rp10_m"], valid["coast_rp_rp10_m"])
        meta = {"pearson_rp10": float(r10.statistic), "p_value_rp10": float(r10.pvalue)}
        save_json(PROCESSED / "rp_correlation_meta.json", meta)
    save_json(PROCESSED / "rp_comparison.json", rp_compare.to_dict(orient="records"))
    rp_compare.to_parquet(PROCESSED / "rp_comparison.parquet", index=False)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--out", type=Path, default=PROCESSED / "gssr_daily_merged.parquet")
    args = parser.parse_args()
    ensure_dirs()
    if not MATCH_PATH.exists():
        raise SystemExit("Run match_stations_to_coastrp.py first")
    merged = merge_all(args.config)
    merged.to_parquet(args.out, index=False)
    print(f"merged {len(merged):,} daily rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

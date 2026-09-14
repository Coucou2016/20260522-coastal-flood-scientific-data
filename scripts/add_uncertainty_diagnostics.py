#!/usr/bin/env python3
"""Add EVT and rank-uncertainty diagnostics for the CEE manuscript.

The earlier workflow already writes non-parametric GSSR bootstrap intervals,
COAST-RP spatial matching ranges, and the 30-station Northwest Europe rank
screen. This script adds two extra diagnostics requested during manuscript
strengthening:

1. A block-maxima GEV 10-year return-level estimate as a parametric robustness
   check against the empirical GSSR RP10.
2. A simple uncertainty propagation for D10 ranks, combining GSSR bootstrap
   ranges with COAST-RP local spatial ranges.
3. A lightweight GSSR reconstruction-envelope diagnostic using the product
   pred_int_lower and pred_int_upper columns where available.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combo1_utils import RAW, extract_gssr_archive  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
FIG_SOURCE = ROOT / "data" / "figure_source"
GSSR_DIR = RAW / "gssr" / "era5"


def stable_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:4], "big")

FOCAL_ARCHIVES = {
    "sheerness-p015-uk": "sheerness_p015_uk.7z",
    "newlyn-p001-uk": "newlyn_p001_uk.7z",
    "aberdeen-p038-uk": "aberdeen_p038_uk.7z",
    "hoekvanholla-hvh-nl": "hoekvanholla_hvh_nl.7z",
    "brest-france": "brest_.7z",
    "newyork-the-battery": "newyork_thebattery__usa.7z",
    "hong-kong-b": "hong_kong_b_329b_china.7z",
    "charleston-sc": "charleston,sc_261a_usa.7z",
}


def empirical_rp10(annual_values: np.ndarray) -> float:
    annual = np.asarray(annual_values, dtype=float)
    annual = annual[np.isfinite(annual)]
    if annual.size < 5:
        return float("nan")
    ranked = np.sort(annual)
    positions = np.arange(1, len(ranked) + 1, dtype=float) / (len(ranked) + 1.0)
    if 0.9 > positions[-1]:
        return float("nan")
    return float(np.interp(0.9, positions, ranked))


def gev_rp(annual_values: np.ndarray, return_period: float = 10.0) -> tuple[float, float, float, float, str]:
    annual = np.asarray(annual_values, dtype=float)
    annual = annual[np.isfinite(annual)]
    if annual.size < 15:
        return float("nan"), float("nan"), float("nan"), float("nan"), "insufficient annual maxima"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            shape, loc, scale = stats.genextreme.fit(annual)
        if not np.isfinite(scale) or scale <= 0:
            return float("nan"), float(shape), float(loc), float(scale), "invalid scale"
        quantile = 1.0 - 1.0 / return_period
        estimate = float(stats.genextreme.ppf(quantile, shape, loc=loc, scale=scale))
        if not np.isfinite(estimate):
            return float("nan"), float(shape), float(loc), float(scale), "non-finite estimate"
        return estimate, float(shape), float(loc), float(scale), "ok"
    except Exception as exc:  # noqa: BLE001
        return float("nan"), float("nan"), float("nan"), float("nan"), f"fit failed: {exc}"


def gev_bootstrap_interval(annual_values: np.ndarray, n_boot: int = 500, seed: int = 0) -> tuple[float, float]:
    annual = np.asarray(annual_values, dtype=float)
    annual = annual[np.isfinite(annual)]
    if n_boot <= 0:
        return float("nan"), float("nan")
    if annual.size < 15:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    reps: list[float] = []
    for _ in range(n_boot):
        sample = rng.choice(annual, size=len(annual), replace=True)
        estimate, *_rest, status = gev_rp(sample, 10.0)
        if status == "ok" and np.isfinite(estimate):
            reps.append(estimate)
    if len(reps) < max(30, n_boot // 10):
        return float("nan"), float("nan")
    arr = np.asarray(reps, dtype=float)
    return float(np.nanpercentile(arr, 2.5)), float(np.nanpercentile(arr, 97.5))


def gev_diagnostic_job(payload: tuple[str, np.ndarray, int]) -> dict[str, float | str]:
    """Run one deterministic station-level GEV diagnostic in a worker process."""
    station_id, annual, n_boot = payload
    gev, shape, loc, scale, status = gev_rp(annual, 10.0)
    lo, hi = gev_bootstrap_interval(annual, n_boot=n_boot, seed=stable_seed(station_id))
    empirical = empirical_rp10(annual)
    return {
        "gev_rp10_m": gev,
        "gev_rp10_bootstrap_p025_m": lo,
        "gev_rp10_bootstrap_p975_m": hi,
        "gev_shape_scipy_c": shape,
        "gev_loc_m": loc,
        "gev_scale_m": scale,
        "gev_fit_status": status,
        "gev_minus_empirical_rp10_m": gev - empirical if np.isfinite(gev) else np.nan,
    }


def run_gev_jobs(station_annual: list[tuple[str, np.ndarray]], n_boot: int = 500) -> list[dict[str, float | str]]:
    payloads = [(station_id, annual, n_boot) for station_id, annual in station_annual]
    max_workers = min(len(payloads), max(1, min(8, os.cpu_count() or 1)))
    if max_workers <= 1:
        return [gev_diagnostic_job(payload) for payload in payloads]
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(gev_diagnostic_job, payloads))


def annual_from_daily(daily: pd.DataFrame, station_id: str) -> np.ndarray:
    sub = daily.loc[daily["station_id"].eq(station_id)].copy()
    if sub.empty:
        return np.asarray([], dtype=float)
    return sub.groupby(sub["date"].dt.year)["surge_m"].max().dropna().to_numpy()


def annual_from_archive(archive_name: str) -> np.ndarray:
    archive_path = GSSR_DIR / archive_name
    csv_path = extract_gssr_archive(archive_path, GSSR_DIR / "extracted" / Path(archive_name).stem)
    if csv_path is None:
        return np.asarray([], dtype=float)
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    surge_col = "surge_reconsturcted" if "surge_reconsturcted" in df.columns else "surge"
    return df.groupby(df["date"].dt.year)[surge_col].max().dropna().to_numpy()


def prediction_interval_envelope_from_archive(archive_name: str) -> dict[str, float | str]:
    archive_path = GSSR_DIR / archive_name
    csv_path = extract_gssr_archive(archive_path, GSSR_DIR / "extracted" / Path(archive_name).stem)
    if csv_path is None:
        return {
            "gssr_predint_rp10_lower_m": np.nan,
            "gssr_predint_rp10_upper_m": np.nan,
            "gssr_prediction_interval_status": "archive missing",
        }
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    if "pred_int_lower" not in df.columns or "pred_int_upper" not in df.columns:
        return {
            "gssr_predint_rp10_lower_m": np.nan,
            "gssr_predint_rp10_upper_m": np.nan,
            "gssr_prediction_interval_status": "prediction interval columns missing",
        }
    lower = df.groupby(df["date"].dt.year)["pred_int_lower"].max().dropna().to_numpy()
    upper = df.groupby(df["date"].dt.year)["pred_int_upper"].max().dropna().to_numpy()
    return {
        "gssr_predint_rp10_lower_m": empirical_rp10(lower),
        "gssr_predint_rp10_upper_m": empirical_rp10(upper),
        "gssr_prediction_interval_status": "annual maxima of product 95% prediction bounds",
    }


def evt_rows_from_focal() -> pd.DataFrame:
    daily = pd.read_parquet(PROCESSED / "gssr_daily_merged.parquet")
    water = pd.read_csv(FIG_SOURCE / "Fig2_water_level_divergence.csv")
    prepared = []
    for _, row in water.iterrows():
        station_id = row["station_id"]
        annual = annual_from_daily(daily, station_id)
        prepared.append((row, station_id, annual, prediction_interval_envelope_from_archive(FOCAL_ARCHIVES.get(station_id, ""))))
    diagnostics = run_gev_jobs([(station_id, annual) for _, station_id, annual, _ in prepared])
    rows = []
    for (row, station_id, annual, pred), diagnostic in zip(prepared, diagnostics):
        rows.append(
            {
                "station_id": station_id,
                "n_annual_maxima": int(len(annual)),
                "empirical_rp10_m": empirical_rp10(annual),
                **diagnostic,
                **pred,
            }
        )
    return pd.DataFrame(rows)


def evt_rows_from_extended() -> pd.DataFrame:
    extended = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    prepared = []
    for _, row in extended.iterrows():
        annual = annual_from_archive(row["gssr_archive"])
        station_id = row["station_id"]
        prepared.append((row, station_id, annual, prediction_interval_envelope_from_archive(row["gssr_archive"])))
    diagnostics = run_gev_jobs([(station_id, annual) for _, station_id, annual, _ in prepared])
    rows = []
    for (row, station_id, annual, pred), diagnostic in zip(prepared, diagnostics):
        rows.append(
            {
                "station_id": station_id,
                "station": row["station"],
                "n_annual_maxima": int(len(annual)),
                "empirical_rp10_m": empirical_rp10(annual),
                **diagnostic,
                **pred,
            }
        )
    return pd.DataFrame(rows)


def _coast_bounds(row: pd.Series) -> tuple[float, float, float]:
    nominal = float(row["coast_rp_rp10_m"] if "coast_rp_rp10_m" in row else row["coast_rp_rp10_m"])
    low = row.get("within5km_min_rp10_m", np.nan)
    high = row.get("within5km_max_rp10_m", np.nan)
    if not np.isfinite(low) or not np.isfinite(high):
        low = row.get("coast_rp_within5km_min_m", np.nan)
        high = row.get("coast_rp_within5km_max_m", np.nan)
    if not np.isfinite(low) or not np.isfinite(high):
        rng = row.get("nearest3_range_m", np.nan)
        if not np.isfinite(rng):
            rng = row.get("coast_rp_nearest3_range_m", 0.0)
        low = nominal - float(rng) / 2.0
        high = nominal + float(rng) / 2.0
    low = min(float(low), nominal)
    high = max(float(high), nominal)
    return nominal, low, high


def _gssr_bounds(row: pd.Series) -> tuple[float, float, float]:
    nominal = float(row["gssr_rp10_m"])
    low = row.get("gssr_rp10_bootstrap_p025_m", nominal)
    high = row.get("gssr_rp10_bootstrap_p975_m", nominal)
    if not np.isfinite(low):
        low = nominal
    if not np.isfinite(high):
        high = nominal
    low = min(float(low), nominal)
    high = max(float(high), nominal)
    return nominal, low, high


def propagate_d10_rank_uncertainty(
    df: pd.DataFrame,
    *,
    station_col: str = "station_id",
    n_iter: int = 5000,
    seed: int = 20260629,
    terrain_col: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    work = df.dropna(subset=[station_col, "gssr_rp10_m"]).copy().reset_index(drop=True)
    n = len(work)
    if n == 0:
        return pd.DataFrame(), pd.DataFrame()
    top_n = max(1, math.ceil(0.2 * n))
    ranks = np.zeros((n_iter, n), dtype=float)
    d10_samples = np.zeros((n_iter, n), dtype=float)
    terrain = work[terrain_col].to_numpy(dtype=float) if terrain_col and terrain_col in work.columns else None
    spearman_vals: list[float] = []
    for i in range(n_iter):
        d10 = np.zeros(n, dtype=float)
        for j, (_, row) in enumerate(work.iterrows()):
            coast_nominal, coast_low, coast_high = _coast_bounds(row)
            gssr_nominal, gssr_low, gssr_high = _gssr_bounds(row)
            coast = rng.triangular(coast_low, coast_nominal, coast_high) if coast_low < coast_high else coast_nominal
            gssr = rng.triangular(gssr_low, gssr_nominal, gssr_high) if gssr_low < gssr_high else gssr_nominal
            d10[j] = coast - gssr
        d10_samples[i, :] = d10
        ranks[i, :] = pd.Series(d10).rank(ascending=False, method="min").to_numpy()
        if terrain is not None and np.isfinite(terrain).sum() >= 3:
            spearman_vals.append(float(pd.Series(d10).corr(pd.Series(terrain), method="spearman")))
    rows = []
    for j, row in work.iterrows():
        rank_j = ranks[:, j]
        d10_j = d10_samples[:, j]
        rows.append(
            {
                "station_id": row[station_col],
                "station": row.get("station", row.get("full_label", row[station_col])),
                "D10_nominal_m": float(row.get("D10_m", row.get("coast_rp_rp10_m", np.nan) - row["gssr_rp10_m"])),
                "D10_mc_p025_m": float(np.nanpercentile(d10_j, 2.5)),
                "D10_mc_p500_m": float(np.nanpercentile(d10_j, 50.0)),
                "D10_mc_p975_m": float(np.nanpercentile(d10_j, 97.5)),
                "D10_rank_p05": float(np.nanpercentile(rank_j, 5.0)),
                "D10_rank_p50": float(np.nanpercentile(rank_j, 50.0)),
                "D10_rank_p95": float(np.nanpercentile(rank_j, 95.0)),
                "D10_top20_probability": float(np.mean(rank_j <= top_n)),
            }
        )
    summary = {
        "n_sites": n,
        "n_iter": n_iter,
        "top_n": top_n,
        "D10_rank_uncertainty_method": "triangular Monte Carlo from GSSR bootstrap and COAST-RP local spatial ranges",
    }
    if spearman_vals:
        arr = np.asarray(spearman_vals, dtype=float)
        summary.update(
            {
                "spearman_D10_vs_connected_2m_p025": float(np.nanpercentile(arr, 2.5)),
                "spearman_D10_vs_connected_2m_p500": float(np.nanpercentile(arr, 50.0)),
                "spearman_D10_vs_connected_2m_p975": float(np.nanpercentile(arr, 97.5)),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame([summary])


def merge_optional_outputs() -> None:
    focal_evt = pd.read_csv(FIG_SOURCE / "Fig2_gssr_evt_diagnostics.csv")
    focal_d10 = pd.read_csv(FIG_SOURCE / "Fig2_D10_rank_uncertainty.csv")
    water = pd.read_csv(FIG_SOURCE / "Fig2_water_level_divergence.csv")
    water = water.merge(
        focal_evt[
            [
                "station_id",
                "gev_rp10_m",
                "gev_rp10_bootstrap_p025_m",
                "gev_rp10_bootstrap_p975_m",
                "gev_fit_status",
                "gssr_predint_rp10_lower_m",
                "gssr_predint_rp10_upper_m",
                "gssr_prediction_interval_status",
            ]
        ],
        on="station_id",
        how="left",
    )
    water = water.merge(
        focal_d10[
            [
                "station_id",
                "D10_mc_p025_m",
                "D10_mc_p975_m",
                "D10_rank_p05",
                "D10_rank_p50",
                "D10_rank_p95",
                "D10_top20_probability",
            ]
        ],
        on="station_id",
        how="left",
    )
    water.to_csv(FIG_SOURCE / "Fig2_water_level_divergence_with_uncertainty.csv", index=False)

    extended_evt = pd.read_csv(FIG_SOURCE / "Fig5_gssr_evt_diagnostics.csv")
    extended_d10 = pd.read_csv(FIG_SOURCE / "Fig5_D10_rank_uncertainty.csv")
    extended = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    extended = extended.merge(
        extended_evt[
            [
                "station_id",
                "gev_rp10_m",
                "gev_rp10_bootstrap_p025_m",
                "gev_rp10_bootstrap_p975_m",
                "gev_fit_status",
                "gssr_predint_rp10_lower_m",
                "gssr_predint_rp10_upper_m",
                "gssr_prediction_interval_status",
            ]
        ],
        on="station_id",
        how="left",
    )
    extended = extended.merge(
        extended_d10[
            [
                "station_id",
                "D10_mc_p025_m",
                "D10_mc_p975_m",
                "D10_rank_p05",
                "D10_rank_p50",
                "D10_rank_p95",
                "D10_top20_probability",
            ]
        ],
        on="station_id",
        how="left",
    )
    extended.to_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening_with_uncertainty.csv", index=False)


def main() -> int:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    focal_evt = evt_rows_from_focal()
    focal_evt.to_csv(FIG_SOURCE / "Fig2_gssr_evt_diagnostics.csv", index=False)

    extended_evt = evt_rows_from_extended()
    extended_evt.to_csv(FIG_SOURCE / "Fig5_gssr_evt_diagnostics.csv", index=False)

    focal = pd.read_csv(FIG_SOURCE / "Fig2_water_level_divergence.csv")
    focal_d10, focal_summary = propagate_d10_rank_uncertainty(focal, n_iter=5000, seed=20260629)
    focal_d10.to_csv(FIG_SOURCE / "Fig2_D10_rank_uncertainty.csv", index=False)
    focal_summary.to_csv(FIG_SOURCE / "Fig2_D10_rank_uncertainty_summary.csv", index=False)

    extended = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    extended_d10, extended_summary = propagate_d10_rank_uncertainty(
        extended,
        n_iter=5000,
        seed=20260630,
        terrain_col="connected_2m_lowland_pct",
    )
    extended_d10.to_csv(FIG_SOURCE / "Fig5_D10_rank_uncertainty.csv", index=False)
    extended_summary.to_csv(FIG_SOURCE / "Fig5_D10_rank_uncertainty_summary.csv", index=False)

    merge_optional_outputs()
    print("Wrote EVT, GSSR prediction-interval, and D10 uncertainty diagnostics")
    print(focal_evt[["station_id", "empirical_rp10_m", "gev_rp10_m", "gssr_predint_rp10_lower_m", "gssr_predint_rp10_upper_m", "gev_fit_status"]].to_string(index=False))
    print(extended_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

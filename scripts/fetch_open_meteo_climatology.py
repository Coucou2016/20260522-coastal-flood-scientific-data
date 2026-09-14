#!/usr/bin/env python3
"""Aggregate Open-Meteo hourly JSON to daily driver table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from combo1_utils import CONFIG, PROCESSED, RAW, ensure_dirs, load_config

OM_DIR = RAW / "open_meteo" / "hourly"


def load_om_json(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    hourly = payload["data"]["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.floor("D")
    daily = df.groupby("date").agg(
        pressure_msl_min=("pressure_msl", "min"),
        wind_speed_10m_max=("wind_speed_10m", "max"),
        wind_gusts_10m_max=("wind_gusts_10m", "max"),
        precipitation_sum=("precipitation", "sum"),
        temperature_2m_mean=("temperature_2m", "mean"),
    )
    meta = payload.get("meta", {})
    daily["station_id"] = meta.get("station_id", path.stem.split("_")[0])
    return daily.reset_index()


def build_daily_table(om_dir: Path = OM_DIR) -> pd.DataFrame:
    frames = []
    for path in sorted(om_dir.glob("*_era5.json")):
        if "1980" not in path.name and "2013" not in path.name:
            continue
        try:
            frames.append(load_om_json(path))
        except (KeyError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: {exc}")
    if not frames:
        raise FileNotFoundError(f"No climatology JSON in {om_dir}")
    return pd.concat(frames, ignore_index=True)


def correlate_with_gssr(drivers: pd.DataFrame, gssr_path: Path) -> pd.DataFrame:
    gssr = pd.read_parquet(gssr_path)
    gssr["date"] = pd.to_datetime(gssr["date"]).dt.floor("D")
    rows = []
    for sid, gdf in gssr.groupby("station_id"):
        ddf = drivers[drivers["station_id"] == sid]
        if ddf.empty:
            continue
        merged = gdf.merge(ddf, on="date", how="inner")
        if len(merged) < 30:
            continue
        from scipy import stats

        rows.append(
            {
                "station_id": sid,
                "n_days": len(merged),
                "spearman_surge_vs_pressure": float(
                    stats.spearmanr(merged["surge_m"], merged["pressure_msl_min"]).correlation
                ),
                "spearman_surge_vs_wind": float(
                    stats.spearmanr(merged["surge_m"], merged["wind_speed_10m_max"]).correlation
                ),
                "spearman_surge_vs_precip": float(
                    stats.spearmanr(merged["surge_m"], merged["precipitation_sum"]).correlation
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--om-dir", type=Path, default=OM_DIR)
    parser.add_argument("--out", type=Path, default=PROCESSED / "drivers_daily.parquet")
    args = parser.parse_args()
    ensure_dirs()
    daily = build_daily_table(args.om_dir)
    daily.to_parquet(args.out, index=False)
    print(f"daily drivers: {len(daily):,} rows -> {args.out}")

    gssr_path = PROCESSED / "gssr_daily_merged.parquet"
    if gssr_path.exists():
        corr = correlate_with_gssr(daily, gssr_path)
        corr.to_parquet(PROCESSED / "driver_surge_correlations.parquet", index=False)
        print(f"driver correlations -> {PROCESSED / 'driver_surge_correlations.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

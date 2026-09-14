#!/usr/bin/env python3
"""Match GSSR tide gauges to nearest COAST-RP coastal points."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree

from combo1_utils import CONFIG, PROCESSED, RP_VARS, ensure_dirs, haversine_km, load_config, save_json

ROOT = Path(__file__).resolve().parents[1]
COAST_NC = ROOT / "data" / "raw" / "coast_rp" / "extracted" / "COAST-RP.nc"


def match_stations(config_path: Path = CONFIG, coast_nc: Path = COAST_NC) -> pd.DataFrame:
    cfg = load_config(config_path)
    ds = xr.open_dataset(coast_nc)
    lon = ds["station_x_coordinate"].values
    lat = ds["station_y_coordinate"].values
    tree = cKDTree(np.column_stack([lon, lat]))

    rows = []
    for st in cfg["stations"]:
        dist_deg, idx = tree.query([[st["lon"], st["lat"]]], k=1)
        idx = int(idx[0])
        dist_km = haversine_km(st["lon"], st["lat"], float(lon[idx]), float(lat[idx]))
        match_flag = "long" if dist_km > 25.0 else "ok"
        row = {
            "station_id": st["id"],
            "station_name": st["name"],
            "station_lat": st["lat"],
            "station_lon": st["lon"],
            "coast_rp_idx": idx,
            "coast_rp_lon": float(lon[idx]),
            "coast_rp_lat": float(lat[idx]),
            "coast_rp_station_id": str(ds["station_id"].values[idx]),
            "match_dist_km": dist_km,
            "match_flag": match_flag,
        }
        for rp, var in RP_VARS.items():
            val = float(ds[var].values[idx])
            row[f"coast_rp_rp{rp}_m"] = val
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--out", type=Path, default=PROCESSED / "coast_rp_nearest.parquet")
    args = parser.parse_args()
    ensure_dirs()
    df = match_stations(args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    save_json(PROCESSED / "coast_rp_nearest.json", df.to_dict(orient="records"))
    long_matches = df[df["match_flag"] == "long"]
    if len(long_matches):
        print(f"WARN {len(long_matches)} station(s) with match_dist_km > 25 km:")
        for _, r in long_matches.iterrows():
            print(f"  {r['station_id']}: {r['match_dist_km']:.1f} km")
    print(f"matched {len(df)} stations -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

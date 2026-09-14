#!/usr/bin/env python3
"""Round-1 truth audit: print evidence for combo1-quality-audit.md."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from combo1_utils import CONFIG, PROCESSED, RAW, RP_VARS, load_config, read_gssr_station

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path, nbytes: int = 65536) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()[:16]


def audit_gssr():
    cfg = load_config()
    print("\n=== GSSR ===")
    for st in cfg["stations"]:
        arch = RAW / "gssr" / "era5" / st["gssr_archive"]
        print(f"\n{st['id']}: archive exists={arch.exists()} size={arch.stat().st_size if arch.exists() else 0}")
        if arch.exists():
            print(f"  sha256(head): {file_hash(arch)}")
        try:
            df = read_gssr_station(st)
            print(f"  rows={len(df)} range={df['date'].min()} .. {df['date'].max()}")
            print(f"  surge_m: min={df['surge_m'].min():.3f} max={df['surge_m'].max():.3f} mean={df['surge_m'].mean():.3f} p99={df['surge_m'].quantile(0.99):.3f}")
            annual = df.groupby(df["date"].dt.year)["surge_m"].max()
            print(f"  annual_max: min={annual.min():.3f} max={annual.max():.3f} n_years={len(annual)}")
        except Exception as exc:
            print(f"  READ ERROR: {exc}")


def audit_coastrp():
    nc = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
    print("\n=== COAST-RP ===")
    print(f"nc exists={nc.exists()} size={nc.stat().st_size if nc.exists() else 0}")
    if not nc.exists():
        return
    ds = xr.open_dataset(nc)
    print(f"dims: {dict(ds.dims)}")
    print(f"vars sample: {list(ds.data_vars)[:8]}...")
    for rp, var in [(10, RP_VARS[10]), (100, RP_VARS[100])]:
        v = ds[var].values
        print(f"  {var}: min={np.nanmin(v):.3f} max={np.nanmax(v):.3f} mean={np.nanmean(v):.3f}")
    print(f"  lon range: {float(ds['station_x_coordinate'].min()):.2f} .. {float(ds['station_x_coordinate'].max()):.2f}")
    print(f"  lat range: {float(ds['station_y_coordinate'].min()):.2f} .. {float(ds['station_y_coordinate'].max()):.2f}")
    ds.close()


def audit_open_meteo():
    print("\n=== Open-Meteo ===")
    hourly = RAW / "open_meteo" / "hourly"
    if not hourly.exists():
        print("  hourly dir missing")
        return
    for p in sorted(hourly.glob("*.parquet"))[:3]:
        df = pd.read_parquet(p)
        print(f"\n{p.name}: cols={list(df.columns)} rows={len(df)}")
        if "time" in df.columns:
            print(f"  time {df['time'].min()} .. {df['time'].max()}")
        for c in ("pressure_msl", "wind_speed_10m_max", "precipitation_sum"):
            if c in df.columns:
                print(f"  {c}: min={df[c].min()} max={df[c].max()} mean={df[c].mean():.3f}")


def audit_deltadtm_sheerness():
    import rasterio
    from rasterio.windows import from_bounds

    print("\n=== DeltaDTM Sheerness bbox ===")
    bbox = (0.69306, 51.392, 0.79306, 51.492)
    tiles_dir = RAW / "deltadtm" / "tiles"
    tifs = list(tiles_dir.rglob("*.tif"))
    print(f"tif count under tiles: {len(tifs)}")
    for tif in tifs[:5]:
        print(f"  {tif.name} size={tif.stat().st_size}")
    target = tiles_dir / "DeltaDTM_v1_1_N51E000.tif"
    if not target.exists():
        target = next((t for t in tifs if "N51E000" in t.name), None)
    if target is None:
        print("  NO TIF for Sheerness")
        return
    with rasterio.open(target) as src:
        print(f"file: {target.name}")
        print(f"  crs={src.crs} res={src.res} shape={src.shape} nodata={src.nodata}")
        print(f"  bounds={src.bounds}")
        window = from_bounds(*bbox, transform=src.transform)
        elev = src.read(1, window=window, masked=True).astype(float)
        valid = np.isfinite(elev.compressed()) if hasattr(elev, "compressed") else np.isfinite(np.ma.filled(elev, np.nan))
        arr = np.ma.filled(elev, np.nan)
        v = arr[np.isfinite(arr)]
        print(f"  window shape={arr.shape} valid_frac={len(v)/arr.size:.3f}")
        if len(v):
            print(f"  elev valid: min={v.min():.3f} max={v.max():.3f} mean={v.mean():.3f} median={np.median(v):.3f}")
            for slr in (0.5, 1.0, 2.0):
                frac = (slr - v > 0).sum() / len(v)  # wrong: need grid
            frac2 = (np.maximum(0, 2.0 - arr) > 0).sum() / np.isfinite(arr).sum()
            print(f"  bathtub +2m flooded_frac (all finite cells)={frac2:.3f}")
            low = v[v < 2.0]
            print(f"  cells below 2m elev: {len(low)/len(v)*100:.1f}% of valid")
            below0 = (v < 0).sum() / len(v)
            print(f"  cells below 0m (EGM2008): {below0*100:.1f}%")


def audit_match():
    print("\n=== Station match ===")
    df = pd.read_parquet(PROCESSED / "coast_rp_nearest.parquet")
    print(df[["station_id", "match_dist_km", "coast_rp_rp10_m", "gssr_rp10_m" if "gssr_rp10_m" in df.columns else "coast_rp_lon"]].to_string() if "gssr_rp10_m" not in df.columns else df[["station_id", "match_dist_km", "coast_rp_rp10_m", "coast_rp_lon", "coast_rp_lat"]].to_string())


def main():
    audit_gssr()
    audit_coastrp()
    audit_open_meteo()
    audit_deltadtm_sheerness()
    audit_match()
    if (PROCESSED / "rp_comparison.parquet").exists():
        rp = pd.read_parquet(PROCESSED / "rp_comparison.parquet")
        print("\n=== RP comparison ===")
        print(rp[["station_id", "gssr_rp10_m", "coast_rp_rp10_m", "rp10_bias_m", "match_dist_km"]].to_string())


if __name__ == "__main__":
    main()

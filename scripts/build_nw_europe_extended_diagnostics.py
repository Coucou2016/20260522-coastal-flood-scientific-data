#!/usr/bin/env python3
"""Build an expanded NW Europe process-terrain screening subset.

The original manuscript used five European DeltaDTM windows. This script
extends the ranking diagnostic to a 30-station NW Europe subset using local
GSSR metadata, COAST-RP, and the already downloaded DeltaDTM Europe.zip.
"""

from __future__ import annotations

import json
import hashlib
import math
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combo1_utils import RAW, extract_gssr_archive, haversine_km  # noqa: E402
from inundation_sensitivity import coastal_mask, load_dem, valid_mask  # noqa: E402
from make_cee_refined_figures import flood_connectivity_layers  # noqa: E402

GSSR_META = RAW / "gssr" / "metadata" / "eraint.geojson"
GSSR_DIR = RAW / "gssr" / "era5"
COAST_NC = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
TILE_INDEX = RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg"
EUROPE_ZIP = RAW / "deltadtm" / "zips" / "Europe.zip"
TILES_DIR = RAW / "deltadtm" / "tiles"
FIG_SOURCE = ROOT / "data" / "figure_source"

GSSR_API = "https://api.github.com/repos/moinabyssinia/gssr/contents/erafive?ref=gh-pages"
GSSR_RAW_BASE = "https://raw.githubusercontent.com/moinabyssinia/gssr/gh-pages/erafive/"

CORE_SITE_IDS = {
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest",
}


def ensure_dirs() -> None:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    GSSR_DIR.mkdir(parents=True, exist_ok=True)
    TILES_DIR.mkdir(parents=True, exist_ok=True)


def slug_from_path(path_text: str) -> str:
    stem = Path(path_text).stem
    stem = stem.strip()
    slug = stem.replace("_", "-").strip("-")
    return slug


def archive_from_path(path_text: str) -> str:
    stem = Path(path_text).stem
    return stem.replace("-", "_") + ".7z"


def display_name(slug: str, tg: str) -> str:
    aliases = {
        "brest": "Brest",
        "hoekvanholla-hvh-nl": "Hoek van Holland",
        "newlyn-p001-uk": "Newlyn",
        "aberdeen-p038-uk": "Aberdeen",
        "sheerness-p015-uk": "Sheerness",
    }
    if slug in aliases:
        return aliases[slug]
    name = Path(tg).stem
    for suffix in ["-bodc", "-refmar", "-rws", "-dmi", "-bsh", "-statkart", "-uhslc"]:
        name = name.replace(suffix, "")
    parts = [p for p in name.replace("_", "-").split("-") if p]
    return " ".join(p.capitalize() for p in parts[:3]) if parts else slug


def github_archives() -> dict[str, str]:
    cache = FIG_SOURCE / "gssr_erafive_github_listing.json"
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        req = Request(GSSR_API, headers={"User-Agent": "coastal-flood-screening"})
        with urlopen(req, timeout=90) as resp:
            payload = json.load(resp)
        cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {item["name"]: item.get("download_url") or f"{GSSR_RAW_BASE}{item['name']}" for item in payload}


def select_subset(n: int = 30) -> pd.DataFrame:
    meta = gpd.read_file(GSSR_META)
    meta["lon"] = meta.geometry.x.astype(float)
    meta["lat"] = meta.geometry.y.astype(float)
    meta["station_id"] = meta["path"].map(slug_from_path)
    meta["gssr_archive"] = meta["path"].map(archive_from_path)
    meta["station"] = [display_name(sid, tg) for sid, tg in zip(meta["station_id"], meta["tg"])]
    archives = github_archives()
    meta = meta[meta["gssr_archive"].isin(archives)].copy()
    # A compact NW Europe / northeast Atlantic window. The lower num_year
    # threshold keeps Sheerness in the subset because it is central to the
    # process-terrain contrast.
    candidates = meta[
        meta["lon"].between(-9.0, 9.0)
        & meta["lat"].between(47.0, 61.0)
        & meta["num_year"].ge(25)
        & meta["corrn"].ge(0.55)
    ].copy()
    candidates["core"] = candidates["station_id"].isin(CORE_SITE_IDS)
    candidates = candidates.sort_values(["core", "num_year", "corrn"], ascending=[False, False, False])
    core = candidates[candidates["core"]].copy()
    fill = candidates[~candidates["core"]].sort_values(["num_year", "corrn"], ascending=False).head(max(0, n - len(core)))
    subset = pd.concat([core, fill], ignore_index=True).drop_duplicates("station_id").head(n).copy()
    subset["subset"] = "NW Europe 30-station screening subset"
    subset[
        ["station_id", "station", "tg", "lat", "lon", "num_year", "corrn", "rmse", "gssr_archive", "subset"]
    ].to_csv(FIG_SOURCE / "Fig5_extended_station_subset.csv", index=False)
    return subset


def download_url(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size >= 200_000:
        return
    if dest.exists():
        dest.unlink()
    print(f"download {dest.name}", flush=True)
    req = Request(url, headers={"User-Agent": "coastal-flood-screening"})
    with urlopen(req, timeout=180) as resp, dest.open("wb") as out:
        while True:
            block = resp.read(1024 * 1024)
            if not block:
                break
            out.write(block)


def read_gssr_archive(row: pd.Series, archives: dict[str, str]) -> pd.DataFrame:
    archive_name = row["gssr_archive"]
    archive_path = GSSR_DIR / archive_name
    download_url(archives[archive_name], archive_path)
    csv_path = extract_gssr_archive(archive_path, GSSR_DIR / "extracted" / Path(archive_name).stem)
    if csv_path is None:
        raise FileNotFoundError(f"No extracted CSV for {archive_name}")
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    surge_col = "surge_reconsturcted" if "surge_reconsturcted" in df.columns else "surge"
    df = df.rename(columns={surge_col: "surge_m"})
    return df[["date", "surge_m"]].dropna()


def empirical_rp10(annual_values: np.ndarray) -> float:
    annual = np.asarray(annual_values, dtype=float)
    annual = annual[np.isfinite(annual)]
    if annual.size < 5:
        return float("nan")
    ranked = np.sort(annual)
    positions = np.arange(1, len(ranked) + 1, dtype=float) / (len(ranked) + 1.0)
    target = 0.9
    if target > positions[-1]:
        return float("nan")
    return float(np.interp(target, positions, ranked))


def stable_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:4], "big")


def gssr_metrics(row: pd.Series, archives: dict[str, str]) -> dict[str, float]:
    df = read_gssr_archive(row, archives)
    annual = df.groupby(df["date"].dt.year)["surge_m"].max().dropna().to_numpy()
    rp10 = empirical_rp10(annual)
    rng = np.random.default_rng(stable_seed(str(row["station_id"])))
    reps = []
    for _ in range(1000):
        reps.append(empirical_rp10(rng.choice(annual, size=len(annual), replace=True)))
    reps = np.asarray(reps, dtype=float)
    return {
        "gssr_years": int(len(annual)),
        "gssr_rp10_m": rp10,
        "gssr_rp10_bootstrap_p025_m": float(np.nanpercentile(reps, 2.5)),
        "gssr_rp10_bootstrap_p975_m": float(np.nanpercentile(reps, 97.5)),
    }


def coast_rp_metrics(stations: pd.DataFrame) -> pd.DataFrame:
    ds = xr.open_dataset(COAST_NC)
    lon = ds["station_x_coordinate"].values.astype(float)
    lat = ds["station_y_coordinate"].values.astype(float)
    rp10 = ds["storm_tide_rp_0010"].values.astype(float)
    rows = []
    for _, st in stations.iterrows():
        dist = np.array([haversine_km(float(st["lon"]), float(st["lat"]), float(x), float(y)) for x, y in zip(lon, lat)])
        order = np.argsort(dist)
        nearest3 = order[:3]
        within5 = order[dist[order] <= 5.0]
        rows.append(
            {
                "station_id": st["station_id"],
                "coast_rp_idx": int(order[0]),
                "coast_rp_lon": float(lon[order[0]]),
                "coast_rp_lat": float(lat[order[0]]),
                "match_dist_km": float(dist[order[0]]),
                "coast_rp_rp10_m": float(rp10[order[0]]),
                "coast_rp_nearest3_range_m": float(np.nanmax(rp10[nearest3]) - np.nanmin(rp10[nearest3])),
                "coast_rp_within5km_n": int(len(within5)),
                "coast_rp_within5km_min_m": float(np.nanmin(rp10[within5])) if len(within5) else np.nan,
                "coast_rp_within5km_max_m": float(np.nanmax(rp10[within5])) if len(within5) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def bbox_for_station(lon: float, lat: float, buffer_deg: float = 0.04) -> tuple[float, float, float, float]:
    return lon - buffer_deg, lat - buffer_deg, lon + buffer_deg, lat + buffer_deg


def ensure_tiles_for_bbox(bbox: tuple[float, float, float, float]) -> list[str]:
    if not EUROPE_ZIP.exists():
        raise FileNotFoundError(f"Missing {EUROPE_ZIP}")
    gdf = gpd.read_file(TILE_INDEX)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    region = box(*bbox)
    tiles = gdf[gdf.intersects(region)].copy()
    needed = [str(t) for t in tiles["tile"]]
    existing = []
    for tile in needed:
        found = list(TILES_DIR.rglob(f"*{Path(tile).stem}*.tif"))
        existing.extend(str(p.name) for p in found)
    missing = [tile for tile in needed if not list(TILES_DIR.rglob(f"*{Path(tile).stem}*.tif"))]
    if missing:
        stems = {Path(tile).stem for tile in missing}
        with zipfile.ZipFile(EUROPE_ZIP) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".tif")]
            for member in members:
                base = Path(member).name
                if not any(stem in base for stem in stems):
                    continue
                target = TILES_DIR / base
                if target.exists() and target.stat().st_size > 0:
                    continue
                print(f"extract {base}", flush=True)
                zf.extract(member, TILES_DIR)
                pulled = TILES_DIR / member
                if pulled.exists() and pulled != target:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    pulled.replace(target)
    return needed


def terrain_metrics(row: pd.Series) -> dict[str, float | str]:
    bbox = bbox_for_station(float(row["lon"]), float(row["lat"]))
    tiles = ensure_tiles_for_bbox(bbox)
    lon2d, lat2d, elev, source, _, _ = load_dem(bbox, allow_synthetic=False)
    valid = valid_mask(elev)
    coast = coastal_mask(elev, valid)
    denom = int(coast.sum())
    if denom == 0:
        return {
            "terrain_status": "no coastal-lowland cells",
            "terrain_tiles": ";".join(tiles),
            "coastal_lowland_cells": 0,
            "connected_2m_lowland_pct": np.nan,
            "bathtub_2m_lowland_pct": np.nan,
            "unconnected_2m_lowland_pct": np.nan,
        }
    layers = flood_connectivity_layers(elev, valid, 2.0, connectivity=8)
    below = layers["low"] & coast
    connected = layers["connected"] & coast
    shifts = {}
    for shift in [-1.0, -0.5, 0.5, 1.0]:
        shifted = flood_connectivity_layers(elev + shift, valid, 2.0, connectivity=8)["connected"] & coast
        shifts[shift] = 100 * shifted.sum() / denom
    return {
        "terrain_status": "ok",
        "terrain_source": source,
        "terrain_tiles": ";".join(tiles),
        "coastal_lowland_cells": denom,
        "median_lowland_elev_m": float(np.nanmedian(elev[coast])),
        "connected_2m_lowland_pct": float(100 * connected.sum() / denom),
        "bathtub_2m_lowland_pct": float(100 * below.sum() / denom),
        "unconnected_2m_lowland_pct": float(100 * (below & ~connected).sum() / denom),
        "connected_2m_dem_pm05_min_pct": float(min(shifts[-0.5], shifts[0.5])),
        "connected_2m_dem_pm05_max_pct": float(max(shifts[-0.5], shifts[0.5])),
        "connected_2m_dem_pm1_min_pct": float(min(shifts[-1.0], shifts[1.0])),
        "connected_2m_dem_pm1_max_pct": float(max(shifts[-1.0], shifts[1.0])),
    }


def build_extended_subset(n: int = 30) -> pd.DataFrame:
    ensure_dirs()
    archives = github_archives()
    subset = select_subset(n)
    coast = coast_rp_metrics(subset)
    rows = []
    for i, (_, row) in enumerate(subset.iterrows(), start=1):
        print(f"[{i}/{len(subset)}] {row['station_id']}", flush=True)
        base = row[
            ["station_id", "station", "tg", "lat", "lon", "num_year", "corrn", "rmse", "gssr_archive", "subset"]
        ].to_dict()
        try:
            base.update(gssr_metrics(row, archives))
        except Exception as exc:  # noqa: BLE001
            base.update({"gssr_error": str(exc)})
        try:
            base.update(terrain_metrics(row))
        except Exception as exc:  # noqa: BLE001
            base.update({"terrain_status": "error", "terrain_error": str(exc)})
        rows.append(base)
    out = pd.DataFrame(rows).merge(coast, on="station_id", how="left")
    out["D10_m"] = out["coast_rp_rp10_m"] - out["gssr_rp10_m"]
    ok = out.dropna(subset=["coast_rp_rp10_m", "connected_2m_lowland_pct"]).copy()
    ok["coast_rp_rank"] = ok["coast_rp_rp10_m"].rank(ascending=False, method="min").astype(int)
    ok["terrain_rank"] = ok["connected_2m_lowland_pct"].rank(ascending=False, method="min").astype(int)
    ok["rank_mismatch_terrain_minus_coast"] = ok["terrain_rank"] - ok["coast_rp_rank"]
    out = out.merge(
        ok[["station_id", "coast_rp_rank", "terrain_rank", "rank_mismatch_terrain_minus_coast"]],
        on="station_id",
        how="left",
    )
    out.to_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv", index=False)
    top_n = max(1, math.ceil(0.2 * len(ok)))
    top_water = set(ok.nsmallest(top_n, "coast_rp_rank")["station_id"])
    top_terrain = set(ok.nsmallest(top_n, "terrain_rank")["station_id"])
    diag = pd.DataFrame(
        [
            {
                "n_sites": int(len(ok)),
                "top_fraction_used": 0.2,
                "top_n": top_n,
                "top_water_sites": ";".join(sorted(top_water)),
                "top_terrain_sites": ";".join(sorted(top_terrain)),
                "top_rank_mismatch_fraction": float(1 - len(top_water & top_terrain) / top_n),
                "spearman_coastrp_vs_connected_2m": float(ok["coast_rp_rp10_m"].corr(ok["connected_2m_lowland_pct"], method="spearman")),
                "kendall_coastrp_vs_connected_2m": float(ok["coast_rp_rp10_m"].corr(ok["connected_2m_lowland_pct"], method="kendall")),
                "spearman_D10_vs_connected_2m": float(ok["D10_m"].corr(ok["connected_2m_lowland_pct"], method="spearman")),
            }
        ]
    )
    diag.to_csv(FIG_SOURCE / "Fig5_nw_europe_rank_mismatch_diagnostics.csv", index=False)
    print(diag.to_string(index=False))
    return out


def main() -> int:
    build_extended_subset(30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

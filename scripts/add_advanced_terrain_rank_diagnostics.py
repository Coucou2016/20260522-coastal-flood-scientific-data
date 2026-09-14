#!/usr/bin/env python3
"""Add terrain/rank diagnostics requested during final submission review.

This script deliberately writes new source tables instead of overwriting the
earlier manuscript tables. It adds:

* fixed physical-size terrain windows (10 x 10 km approximation);
* cell-area based km2 metrics in addition to lowland fractions;
* all spatially eligible COAST-RP + DeltaDTM stations as the main rank sample;
* top-k overlap curves against a permutation null envelope;
* two-sided permutation p-values for raw COAST-RP versus terrain metrics;
* an explicit audit row noting that official DeltaDTM mask tiles are not
  present locally, so current connectivity still uses a boundary-nodata proxy.
"""

from __future__ import annotations

import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
from scipy import stats
from scipy import ndimage as ndi
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combo1_utils import RAW  # noqa: E402
from inundation_sensitivity import valid_mask  # noqa: E402


FIG_SOURCE = ROOT / "data" / "figure_source"
CANDIDATE_AUDIT = FIG_SOURCE / "Fig5_station_candidate_audit.csv"
BASELINE_30 = FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv"
MASK_ZIP = RAW / "deltadtm" / "zips" / "mask_tiles.zip"
ELEV_ZIP = RAW / "deltadtm" / "zips" / "Europe.zip"
TILE_INDEX = RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg"
TILES_DIR = RAW / "deltadtm" / "tiles"

EARTH_RADIUS_KM = 6371.0088
LEVELS_M = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
DEM_SHIFTS_M = [-1.0, -0.5, 0.5, 1.0]
LOWLAND_MAX_M = 15.0
_TILE_INDEX_GDF: gpd.GeoDataFrame | None = None


STRUCTURE_8 = np.ones((3, 3), dtype=bool)


def fixed_km_bbox(lon: float, lat: float, width_km: float = 10.0) -> tuple[float, float, float, float]:
    """Approximate a square lon/lat crop with fixed physical width."""
    half = width_km / 2.0
    lat_span = half / 110.574
    lon_span = half / (111.320 * max(math.cos(math.radians(lat)), 0.15))
    return lon - lon_span, lat - lat_span, lon + lon_span, lat + lat_span


def tile_index() -> gpd.GeoDataFrame:
    global _TILE_INDEX_GDF
    if _TILE_INDEX_GDF is None:
        gdf = gpd.read_file(TILE_INDEX)
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        _TILE_INDEX_GDF = gdf
    return _TILE_INDEX_GDF


def tile_paths_for_bbox(bbox: tuple[float, float, float, float]) -> list[Path]:
    gdf = tile_index()
    rows = gdf[gdf.intersects(box(*bbox))]
    paths: list[Path] = []
    missing_stems: list[str] = []
    for tile in rows["tile"].astype(str):
        stem = Path(tile).stem
        found = sorted(p for p in TILES_DIR.rglob(f"*{stem}*.tif") if p.stat().st_size > 100_000)
        if found:
            paths.extend(found)
        else:
            missing_stems.append(stem)
    if missing_stems and ELEV_ZIP.exists():
        with zipfile.ZipFile(ELEV_ZIP) as zf:
            for member in zf.namelist():
                if not member.lower().endswith(".tif"):
                    continue
                base = Path(member).name
                if not any(stem in base for stem in missing_stems):
                    continue
                target = TILES_DIR / base
                if not target.exists():
                    zf.extract(member, TILES_DIR)
                    pulled = TILES_DIR / member
                    if pulled.exists() and pulled != target:
                        pulled.replace(target)
                if target.exists() and target.stat().st_size > 100_000:
                    paths.append(target)
    # Merge order must not depend on filesystem traversal order when adjacent
    # tiles overlap by a boundary row or column.
    return sorted({p.resolve() for p in paths}, key=lambda p: p.as_posix().lower())


def cell_center_mesh(transform: rasterio.Affine, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Return true raster-cell centre coordinates for a north-up lon/lat grid."""
    rows, cols = np.indices(shape, dtype=float)
    cols += 0.5
    rows += 0.5
    lon2d = transform.c + transform.a * cols + transform.b * rows
    lat2d = transform.f + transform.d * cols + transform.e * rows
    return lon2d, lat2d


def read_dem_window_fast(
    bbox: tuple[float, float, float, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, dict[str, object], list[str]]:
    paths = tile_paths_for_bbox(bbox)
    if not paths:
        raise FileNotFoundError(f"No local DeltaDTM elevation tile for bbox {bbox}")
    west, south, east, north = bbox
    if len(paths) == 1:
        with rasterio.open(paths[0]) as src:
            window = from_bounds(west, south, east, north, transform=src.transform).round_offsets().round_lengths()
            elev = src.read(1, window=window, boundless=True, masked=True).astype(float)
            elev = np.ma.filled(elev, np.nan)
            out_transform = src.window_transform(window)
            meta = {
                "crs": src.crs,
                "resolution": src.res,
                "nodata": src.nodata,
                "transform": out_transform,
            }
        lon2d, lat2d = cell_center_mesh(out_transform, elev.shape)
        return lon2d, lat2d, elev, f"DeltaDTM:{paths[0].name}", meta, [p.name for p in paths]
    datasets = [rasterio.open(p) for p in paths]
    try:
        mosaic, out_transform = merge(
            datasets,
            bounds=(west, south, east, north),
            res=1 / 3600,
            nodata=-9999.0,
            method="first",
        )
        elev = mosaic[0].astype(float)
        elev[elev <= -9000] = np.nan
        lon2d, lat2d = cell_center_mesh(out_transform, elev.shape)
        meta = {
            "crs": datasets[0].crs,
            "resolution": datasets[0].res,
            "nodata": datasets[0].nodata,
            "transform": out_transform,
        }
        return lon2d, lat2d, elev, f"DeltaDTM:mosaic({len(paths)})", meta, [p.name for p in paths]
    finally:
        for ds in datasets:
            ds.close()


def cell_area_km2(lon2d: np.ndarray, lat2d: np.ndarray) -> np.ndarray:
    """Approximate lon/lat grid-cell areas on a sphere."""
    if lon2d.shape[1] > 1:
        dlon = float(np.nanmedian(np.abs(np.diff(lon2d, axis=1))))
    else:
        dlon = 1 / 3600
    if lat2d.shape[0] > 1:
        dlat = float(np.nanmedian(np.abs(np.diff(lat2d, axis=0))))
    else:
        dlat = 1 / 3600
    area_by_row = (
        EARTH_RADIUS_KM**2
        * math.radians(abs(dlon))
        * math.radians(abs(dlat))
        * np.cos(np.radians(lat2d[:, 0]))
    )
    return np.repeat(area_by_row[:, None], lon2d.shape[1], axis=1)


def sum_area(area: np.ndarray, mask: np.ndarray) -> float:
    return float(np.nansum(np.where(mask, area, 0.0)))


def boundary_seed_from_nodata(valid: np.ndarray) -> np.ndarray:
    ocean_proxy = ~valid
    seed = np.zeros(valid.shape, dtype=bool)
    if valid.size == 0:
        return seed
    seed[0, :] = ocean_proxy[0, :]
    seed[-1, :] = ocean_proxy[-1, :]
    seed[:, 0] |= ocean_proxy[:, 0]
    seed[:, -1] |= ocean_proxy[:, -1]
    return seed


def fast_connectivity_layers(elev: np.ndarray, valid: np.ndarray, eta: float) -> dict[str, np.ndarray]:
    low = valid & np.isfinite(elev) & (elev <= eta)
    ocean_proxy = ~valid
    seed = boundary_seed_from_nodata(valid)
    ocean_reachable = ndi.binary_propagation(seed, structure=STRUCTURE_8, mask=ocean_proxy)
    passable = low | ocean_reachable
    reachable = ndi.binary_propagation(seed, structure=STRUCTURE_8, mask=passable)
    connected = reachable & low
    return {
        "low": low,
        "seed": seed,
        "ocean_reachable": ocean_reachable,
        "connected": connected,
    }


def mask_zip_status() -> dict[str, object]:
    status = {
        "official_mask_tiles_zip_present": MASK_ZIP.exists(),
        "official_mask_tiles_zip_path": str(MASK_ZIP.relative_to(ROOT)) if MASK_ZIP.exists() else "not present",
        "elevation_zip_present": ELEV_ZIP.exists(),
        "elevation_zip_path": str(ELEV_ZIP.relative_to(ROOT)) if ELEV_ZIP.exists() else "not present",
        "official_mask_note": (
            "Official DeltaDTM mask tiles were not present locally; connectivity uses boundary-nodata proxy, "
            "not class-aware ocean/lake/river/255 seeding."
        ),
    }
    if MASK_ZIP.exists():
        with zipfile.ZipFile(MASK_ZIP) as zf:
            names = zf.namelist()
        status["official_mask_tile_count"] = sum(n.lower().endswith((".tif", ".tiff")) for n in names)
        status["official_mask_note"] = (
            "Official mask_tiles.zip is present; class-aware seed implementation still requires explicit extraction "
            "and use of ocean/lake/river/255 classes."
        )
    return status


def terrain_metrics_for_station(row: pd.Series, width_km: float = 10.0) -> dict[str, object]:
    lon = float(row["lon"])
    lat = float(row["lat"])
    bbox = fixed_km_bbox(lon, lat, width_km)
    lon2d, lat2d, elev, source, meta, tiles = read_dem_window_fast(bbox)
    valid = valid_mask(elev)
    area = cell_area_km2(lon2d, lat2d)
    lowland = valid & np.isfinite(elev) & (elev <= LOWLAND_MAX_M)
    denom_area = sum_area(area, lowland)
    window_area = sum_area(area, np.ones(valid.shape, dtype=bool))
    valid_area = sum_area(area, valid)
    capped30 = valid & np.isclose(elev, 30.0, atol=1e-6)
    nodata = ~valid

    out: dict[str, object] = {
        "station_id": row["station_id"],
        "station": row.get("station", row["station_id"]),
        "lat": lat,
        "lon": lon,
        "window_width_km": width_km,
        "bbox_west": bbox[0],
        "bbox_south": bbox[1],
        "bbox_east": bbox[2],
        "bbox_north": bbox[3],
        "terrain_source": source,
        "terrain_tiles": ";".join(tiles),
        "raster_crs": str(meta.get("crs", "")),
        "raster_resolution": str(meta.get("resolution", "")),
        "raster_nodata": meta.get("nodata", ""),
        "window_area_km2": window_area,
        "valid_area_km2": valid_area,
        "coastal_lowland_area_km2": denom_area,
        "coastal_lowland_cells": int(lowland.sum()),
        "valid_cells": int(valid.sum()),
        "nodata_cells": int(nodata.sum()),
        "capped_30m_cells": int(capped30.sum()),
        "capped_30m_area_km2": sum_area(area, capped30),
        "boundary_nodata_seed_proxy": True,
        "official_mask_classes_used": False,
    }
    if denom_area <= 0:
        for level in LEVELS_M:
            prefix = f"{level:g}m"
            out[f"connected_{prefix}_lowland_pct"] = np.nan
            out[f"connected_{prefix}_area_km2"] = np.nan
            out[f"all_below_{prefix}_area_km2"] = np.nan
        return out

    for level in LEVELS_M:
        layers = fast_connectivity_layers(elev, valid, level)
        low = layers["low"] & lowland
        connected = layers["connected"] & lowland
        seed = layers["seed"]
        ocean_reachable = layers["ocean_reachable"]
        prefix = f"{level:g}m"
        conn_area = sum_area(area, connected)
        below_area = sum_area(area, low)
        out[f"connected_{prefix}_lowland_pct"] = 100.0 * conn_area / denom_area
        out[f"all_below_{prefix}_lowland_pct"] = 100.0 * below_area / denom_area
        out[f"unconnected_{prefix}_lowland_pct"] = 100.0 * max(below_area - conn_area, 0.0) / denom_area
        out[f"connected_{prefix}_area_km2"] = conn_area
        out[f"all_below_{prefix}_area_km2"] = below_area
        out[f"unconnected_{prefix}_area_km2"] = max(below_area - conn_area, 0.0)
        out[f"connected_{prefix}_window_pct"] = 100.0 * conn_area / window_area if window_area else np.nan
        out[f"seed_proxy_{prefix}_cells"] = int(seed.sum())
        out[f"boundary_nodata_reachable_{prefix}_cells"] = int(ocean_reachable.sum())
    for shift in DEM_SHIFTS_M:
        layers = fast_connectivity_layers(elev + shift, valid, 2.0)
        conn_area = sum_area(area, layers["connected"] & lowland)
        label = str(shift).replace("-", "m").replace(".", "p")
        out[f"connected_2m_shift_{label}_lowland_pct"] = 100.0 * conn_area / denom_area
        out[f"connected_2m_shift_{label}_area_km2"] = conn_area
    return out


def rank_frame(frame: pd.DataFrame, terrain_col: str, water_col: str = "coast_rp_rp10_m") -> pd.DataFrame:
    out = frame.dropna(subset=[water_col, terrain_col]).copy()
    out["water_rank"] = out[water_col].rank(ascending=False, method="min").astype(int)
    out["terrain_rank"] = out[terrain_col].rank(ascending=False, method="min").astype(int)
    out["terrain_minus_water_rank"] = out["terrain_rank"] - out["water_rank"]
    out["water_minus_terrain_rank"] = out["water_rank"] - out["terrain_rank"]
    return out


def top_overlap_curve(
    frame: pd.DataFrame,
    sample: str,
    terrain_col: str,
    water_col: str = "coast_rp_rp10_m",
    fractions: list[float] | None = None,
    n_perm: int = 10_000,
    seed: int = 20260710,
) -> pd.DataFrame:
    fractions = fractions or [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    ranked = rank_frame(frame, terrain_col, water_col).reset_index(drop=True)
    water = ranked[water_col].to_numpy(float)
    terrain = ranked[terrain_col].to_numpy(float)
    water_rank = stats.rankdata(-water, method="average")
    terrain_rank = stats.rankdata(-terrain, method="average")
    rng = np.random.default_rng(seed)
    permutation_indices = np.vstack([rng.permutation(len(terrain_rank)) for _ in range(n_perm)])
    permuted = terrain_rank[permutation_indices]
    permuted_order = np.argsort(permuted, axis=1, kind="stable")
    rows = []
    n = len(ranked)
    for frac in fractions:
        top_n = max(1, math.ceil(frac * n))
        top_water = set(np.argsort(water_rank)[:top_n].tolist())
        top_terrain = set(np.argsort(terrain_rank)[:top_n].tolist())
        observed_overlap = len(top_water & top_terrain)
        null_overlap = np.isin(
            permuted_order[:, :top_n],
            np.fromiter(top_water, dtype=int),
        ).sum(axis=1).astype(float)
        rows.append(
            {
                "sample": sample,
                "terrain_metric": terrain_col,
                "n_sites": n,
                "top_fraction": frac,
                "top_n": top_n,
                "observed_overlap": observed_overlap,
                "observed_mismatch": 1.0 - observed_overlap / top_n,
                "random_expected_overlap": top_n * top_n / n,
                "random_expected_mismatch": 1.0 - top_n / n,
                "null_overlap_p025": float(np.percentile(null_overlap, 2.5)),
                "null_overlap_p500": float(np.percentile(null_overlap, 50.0)),
                "null_overlap_p975": float(np.percentile(null_overlap, 97.5)),
                "overlap_low_tail_p": float((np.sum(null_overlap <= observed_overlap) + 1) / (n_perm + 1)),
            }
        )
    return pd.DataFrame(rows)


def permutation_assoc(
    frame: pd.DataFrame,
    sample: str,
    terrain_col: str,
    water_col: str = "coast_rp_rp10_m",
    n_perm: int = 10_000,
    seed: int = 20260711,
) -> dict[str, object]:
    ranked = frame.dropna(subset=[water_col, terrain_col]).copy().reset_index(drop=True)
    water = ranked[water_col].to_numpy(float)
    terrain = ranked[terrain_col].to_numpy(float)
    obs_s = float(pd.Series(water).corr(pd.Series(terrain), method="spearman"))
    obs_k = float(pd.Series(water).corr(pd.Series(terrain), method="kendall"))
    rng = np.random.default_rng(seed)
    permutation_indices = np.vstack([rng.permutation(len(terrain)) for _ in range(n_perm)])
    water_rank = stats.rankdata(water, method="average")
    terrain_rank = stats.rankdata(terrain, method="average")
    water_centered = water_rank - water_rank.mean()
    terrain_centered = terrain_rank - terrain_rank.mean()
    permuted_centered = terrain_centered[permutation_indices]
    denominator = np.linalg.norm(water_centered) * np.linalg.norm(terrain_centered)
    s_null = (permuted_centered @ water_centered) / denominator

    tri = np.triu_indices(len(water), k=1)
    water_pair_sign = np.sign(water_rank[:, None] - water_rank[None, :])[tri]
    terrain_non_ties = int(np.count_nonzero(np.sign(terrain_rank[:, None] - terrain_rank[None, :])[tri]))
    kendall_denominator = math.sqrt(float(np.count_nonzero(water_pair_sign)) * terrain_non_ties)
    k_null = np.empty(n_perm, dtype=float)
    for start in range(0, n_perm, 250):
        stop = min(start + 250, n_perm)
        permuted_rank = terrain_rank[permutation_indices[start:stop]]
        pair_sign = np.sign(permuted_rank[:, :, None] - permuted_rank[:, None, :])[:, tri[0], tri[1]]
        k_null[start:stop] = np.sum(pair_sign * water_pair_sign[None, :], axis=1) / kendall_denominator
    return {
        "sample": sample,
        "terrain_metric": terrain_col,
        "n_sites": int(len(ranked)),
        "spearman": obs_s,
        "spearman_two_sided_p": float((np.sum(np.abs(s_null) >= abs(obs_s)) + 1) / (n_perm + 1)),
        "spearman_left_p": float((np.sum(s_null <= obs_s) + 1) / (n_perm + 1)),
        "spearman_null_p025": float(np.percentile(s_null, 2.5)),
        "spearman_null_p975": float(np.percentile(s_null, 97.5)),
        "kendall": obs_k,
        "kendall_two_sided_p": float((np.sum(np.abs(k_null) >= abs(obs_k)) + 1) / (n_perm + 1)),
        "kendall_left_p": float((np.sum(k_null <= obs_k) + 1) / (n_perm + 1)),
        "kendall_null_p025": float(np.percentile(k_null, 2.5)),
        "kendall_null_p975": float(np.percentile(k_null, 97.5)),
    }


def pick_archetypes(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = rank_frame(frame, "connected_2m_lowland_pct")
    n = len(ranked)
    top_n = max(1, math.ceil(0.2 * n))
    ranked["water_top20"] = ranked["water_rank"].le(top_n)
    ranked["terrain_top20"] = ranked["terrain_rank"].le(top_n)
    rows = []
    aligned = ranked[ranked["water_top20"] & ranked["terrain_top20"]].sort_values("connected_2m_lowland_pct", ascending=False)
    if not aligned.empty:
        row = aligned.iloc[0].copy()
        row["archetype"] = "aligned high storm-tide / high connected-terrain"
        rows.append(row)
    high_water_low = ranked[ranked["water_top20"] & ~ranked["terrain_top20"]].sort_values("terrain_minus_water_rank", ascending=False)
    if not high_water_low.empty:
        row = high_water_low.iloc[0].copy()
        row["archetype"] = "high storm-tide / low connected-terrain"
        rows.append(row)
    lower_water_high = ranked[~ranked["water_top20"] & ranked["terrain_top20"]].copy()
    # Prefer non-Dutch examples for the main archetype if available because the
    # Dutch protected lowland cases are already flagged as seed/window sensitive.
    non_dutch = lower_water_high[~lower_water_high["station_id"].str.contains("-nl|delfzijl|denhelder", case=False, na=False)]
    pool = non_dutch if not non_dutch.empty else lower_water_high
    pool = pool.sort_values("water_minus_terrain_rank", ascending=False)
    if not pool.empty:
        row = pool.iloc[0].copy()
        row["archetype"] = "lower storm-tide / high connected-terrain"
        rows.append(row)
    out = pd.DataFrame(rows)
    cols = [
        "archetype",
        "station_id",
        "station",
        "coast_rp_rp10_m",
        "connected_2m_lowland_pct",
        "connected_2m_area_km2",
        "coastal_lowland_area_km2",
        "water_rank",
        "terrain_rank",
        "terrain_minus_water_rank",
        "water_minus_terrain_rank",
    ]
    return out[cols]


def main() -> int:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    audit = pd.read_csv(CANDIDATE_AUDIT)
    spatial = audit[audit["deltadtm_tile_available"].eq(True) & audit["coast_rp_rp10_m"].notna()].copy()
    terrain_path = FIG_SOURCE / "Fig6_fixed10km_terrain_area_metrics.csv"
    if terrain_path.exists():
        cached = pd.read_csv(terrain_path)
        if set(spatial["station_id"]).issubset(set(cached["station_id"])) and "connected_2m_area_km2" in cached.columns:
            terrain = cached[cached["station_id"].isin(set(spatial["station_id"]))].copy()
        else:
            rows = []
            for i, (_, row) in enumerate(spatial.iterrows(), start=1):
                print(f"[{i}/{len(spatial)}] fixed-km terrain {row['station_id']}", flush=True)
                base = row.to_dict()
                try:
                    base.update(terrain_metrics_for_station(row, width_km=10.0))
                    base["advanced_terrain_status"] = "ok"
                except Exception as exc:  # noqa: BLE001
                    base["advanced_terrain_status"] = "error"
                    base["advanced_terrain_error"] = str(exc)
                rows.append(base)
            terrain = pd.DataFrame(rows)
            terrain.to_csv(terrain_path, index=False)
    else:
        rows = []
        for i, (_, row) in enumerate(spatial.iterrows(), start=1):
            print(f"[{i}/{len(spatial)}] fixed-km terrain {row['station_id']}", flush=True)
            base = row.to_dict()
            try:
                base.update(terrain_metrics_for_station(row, width_km=10.0))
                base["advanced_terrain_status"] = "ok"
            except Exception as exc:  # noqa: BLE001
                base["advanced_terrain_status"] = "error"
                base["advanced_terrain_error"] = str(exc)
            rows.append(base)
        terrain = pd.DataFrame(rows)
        terrain.to_csv(terrain_path, index=False)

    mask_audit = pd.DataFrame([mask_zip_status()])
    mask_audit.to_csv(FIG_SOURCE / "Fig6_deltadtm_mask_seed_audit.csv", index=False)

    subsets = {
        "all spatial eligible": terrain,
        "GSSR-qualified corr>=0.55": terrain[
            terrain["archive_available"].eq(True)
            & terrain["passes_years_ge25"].eq(True)
            & terrain["passes_corr_ge055"].eq(True)
        ].copy(),
        "baseline 30-station subset": terrain[terrain["selected_base_30"].eq(True)].copy(),
    }
    rank_rows = []
    overlap_tables = []
    assoc_rows = []
    for sample, frame in subsets.items():
        frame = frame.dropna(subset=["coast_rp_rp10_m", "connected_2m_lowland_pct", "connected_2m_area_km2"]).copy()
        for metric in ["connected_2m_lowland_pct", "connected_2m_area_km2", "connected_2m_window_pct"]:
            ranked = rank_frame(frame, metric)
            top_n = max(1, math.ceil(0.2 * len(ranked)))
            top_w = set(ranked.nsmallest(top_n, "water_rank")["station_id"])
            top_t = set(ranked.nsmallest(top_n, "terrain_rank")["station_id"])
            rank_rows.append(
                {
                    "sample": sample,
                    "terrain_metric": metric,
                    "n_sites": len(ranked),
                    "top_n": top_n,
                    "top_overlap": len(top_w & top_t),
                    "top_mismatch": 1.0 - len(top_w & top_t) / top_n,
                    "random_expected_mismatch": 1.0 - top_n / len(ranked),
                    "spearman": float(ranked["coast_rp_rp10_m"].corr(ranked[metric], method="spearman")),
                    "kendall": float(ranked["coast_rp_rp10_m"].corr(ranked[metric], method="kendall")),
                    "top_water_sites": ";".join(ranked.nsmallest(top_n, "water_rank")["station_id"]),
                    "top_terrain_sites": ";".join(ranked.nsmallest(top_n, "terrain_rank")["station_id"]),
                }
            )
            overlap_tables.append(top_overlap_curve(frame, sample, metric, seed=20260710 + len(overlap_tables)))
            assoc_rows.append(permutation_assoc(frame, sample, metric, seed=20260711 + len(assoc_rows)))
    pd.DataFrame(rank_rows).to_csv(FIG_SOURCE / "Fig6_rank_metrics_fraction_area_samples.csv", index=False)
    pd.concat(overlap_tables, ignore_index=True).to_csv(FIG_SOURCE / "Fig6_topk_overlap_null_envelope.csv", index=False)
    pd.DataFrame(assoc_rows).to_csv(FIG_SOURCE / "Fig6_two_sided_permutation_association.csv", index=False)
    pick_archetypes(subsets["GSSR-qualified corr>=0.55"]).to_csv(FIG_SOURCE / "Fig6_archetype_map_selection.csv", index=False)
    print("Wrote advanced terrain/rank diagnostics")
    print(pd.DataFrame(rank_rows).to_string(index=False))
    print(mask_audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

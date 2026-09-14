#!/usr/bin/env python3
"""Compute DeltaDTM official-mask-aware terrain connectivity diagnostics.

The earlier fixed-window terrain diagnostic used boundary no-data as a marine
seed proxy. This script keeps that proxy result intact and adds a separate
official-mask-aware rerun using DeltaDTM mask classes:

* 0 = land
* 1 = ocean
* 2 = lake
* 3 = river
* 255 = clipped terrain

Ocean cells are the primary marine seed. River cells are included as tidal-water
seed only when they belong to the water component connected to ocean cells
inside the local crop. Only class 0 land cells enter the lowland denominator;
ocean, river, lake and 255 clipped cells are excluded from the land-response
metric.
"""

from __future__ import annotations

import hashlib
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from add_advanced_terrain_rank_diagnostics import (  # noqa: E402
    LEVELS_M,
    LOWLAND_MAX_M,
    STRUCTURE_8,
    cell_area_km2,
    fixed_km_bbox,
    permutation_assoc,
    rank_frame,
    read_dem_window_fast,
    sum_area,
    tile_index,
    top_overlap_curve,
)
from combo1_utils import RAW  # noqa: E402
from inundation_sensitivity import valid_mask  # noqa: E402

FIG_SOURCE = ROOT / "data" / "figure_source"
MASK_ZIP = RAW / "deltadtm" / "zips" / "mask_tiles.zip"
MASK_DIR = RAW / "deltadtm" / "mask_tiles"
FIXED_METRICS = FIG_SOURCE / "Fig6_fixed10km_terrain_area_metrics.csv"

MASK_EXPECTED_SIZE = 428_178_062
MASK_EXPECTED_MD5 = "4fc2bf4e33bd684a5c35f3249808521d"
MAX_PRIMARY_COAST_MATCH_KM = 6.0
MARINE_CONTEXT_WIDTHS_KM = (25.0, 50.0, 100.0, 200.0)

MASK_CLASS_NAMES = {
    0: "land",
    1: "ocean",
    2: "lake",
    3: "river",
    254: "outside_mask_support",
    255: "clipped_255",
}

# Value 255 is a documented DeltaDTM mask class. It must not also be used as
# the array fill value, otherwise crop/mosaic edges are misreported as product
# clipping. Copernicus water-mask classes do not use 254.
MASK_OUTSIDE_SUPPORT = np.uint8(254)


def ensure_mask_zip() -> None:
    if not MASK_ZIP.exists():
        raise FileNotFoundError(
            f"Missing official DeltaDTM mask zip: {MASK_ZIP}. "
            "Download it from the DeltaDTM v1.1 4TU dataset as mask_tiles.zip."
        )
    if MASK_ZIP.stat().st_size != MASK_EXPECTED_SIZE:
        raise RuntimeError(
            f"Unexpected mask_tiles.zip size {MASK_ZIP.stat().st_size}; expected {MASK_EXPECTED_SIZE}."
        )
    digest = hashlib.md5()  # nosec B324 - published file identity, not cryptographic authentication
    with MASK_ZIP.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().lower() != MASK_EXPECTED_MD5:
        raise RuntimeError(
            f"Unexpected mask_tiles.zip MD5 {digest.hexdigest()}; expected {MASK_EXPECTED_MD5}."
        )


def extract_mask_tile(stem: str) -> Path:
    """Extract one mask tile from mask_tiles.zip if needed."""
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    target = MASK_DIR / f"{stem}.tif"
    if target.exists() and target.stat().st_size > 1000:
        return target
    member = f"masks/{stem}.tif"
    with zipfile.ZipFile(MASK_ZIP) as zf:
        if member not in zf.namelist():
            raise FileNotFoundError(f"{member} not found inside {MASK_ZIP}")
        zf.extract(member, MASK_DIR)
    extracted = MASK_DIR / member
    if extracted.exists():
        extracted.replace(target)
    masks_subdir = MASK_DIR / "masks"
    try:
        if masks_subdir.exists() and not any(masks_subdir.iterdir()):
            masks_subdir.rmdir()
    except OSError:
        pass
    return target


def mask_paths_for_bbox(bbox: tuple[float, float, float, float]) -> list[Path]:
    """Resolve official mask tiles from the spatial index, deterministically."""
    from shapely.geometry import box

    rows = tile_index()
    rows = rows[rows.intersects(box(*bbox))]
    paths = [extract_mask_tile(Path(str(tile)).stem) for tile in rows["tile"].astype(str)]
    return sorted({p.resolve() for p in paths}, key=lambda p: p.as_posix().lower())


def read_mask_window(
    bbox: tuple[float, float, float, float],
) -> tuple[np.ndarray, rasterio.Affine, object, str]:
    """Read an official-mask grid and retain its geospatial transform."""
    paths = mask_paths_for_bbox(bbox)
    if not paths:
        raise FileNotFoundError(f"No official DeltaDTM mask paths for bbox: {bbox}")
    west, south, east, north = bbox
    if len(paths) == 1:
        with rasterio.open(paths[0]) as src:
            window = from_bounds(west, south, east, north, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(
                1,
                window=window,
                boundless=True,
                fill_value=int(MASK_OUTSIDE_SUPPORT),
            )
            out_transform = src.window_transform(window)
            crs = src.crs
        return arr.astype(np.uint8), out_transform, crs, paths[0].name
    datasets = [rasterio.open(p) for p in paths]
    try:
        mosaic, out_transform = merge(
            datasets,
            bounds=(west, south, east, north),
            res=1 / 3600,
            nodata=int(MASK_OUTSIDE_SUPPORT),
            dtype="uint8",
            method="first",
        )
        return mosaic[0].astype(np.uint8), out_transform, datasets[0].crs, f"mask:mosaic({len(paths)})"
    finally:
        for ds in datasets:
            ds.close()


def align_mask_to_dem(
    source: np.ndarray,
    source_transform: rasterio.Affine,
    source_crs: object,
    dem_shape: tuple[int, int],
    dem_transform: rasterio.Affine,
    dem_crs: object,
) -> np.ndarray:
    """Nearest-neighbour geospatial alignment; never resize by array shape."""
    destination = np.full(dem_shape, MASK_OUTSIDE_SUPPORT, dtype=np.uint8)
    reproject(
        source=source,
        destination=destination,
        src_transform=source_transform,
        src_crs=source_crs,
        src_nodata=int(MASK_OUTSIDE_SUPPORT),
        dst_transform=dem_transform,
        dst_crs=dem_crs,
        dst_nodata=int(MASK_OUTSIDE_SUPPORT),
        resampling=Resampling.nearest,
    )
    return destination


def align_binary_to_dem(
    source: np.ndarray,
    source_transform: rasterio.Affine,
    source_crs: object,
    dem_shape: tuple[int, int],
    dem_transform: rasterio.Affine,
    dem_crs: object,
) -> np.ndarray:
    destination = np.zeros(dem_shape, dtype=np.uint8)
    reproject(
        source=source.astype(np.uint8),
        destination=destination,
        src_transform=source_transform,
        src_crs=source_crs,
        dst_transform=dem_transform,
        dst_crs=dem_crs,
        dst_nodata=0,
        resampling=Resampling.nearest,
    )
    return destination.astype(bool)


def resolve_marine_seed(
    lon: float,
    lat: float,
    bbox: tuple[float, float, float, float],
    dem_shape: tuple[int, int],
    dem_transform: rasterio.Affine,
    dem_crs: object,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Resolve ocean-connected water using an adaptive context around the analysis crop."""
    raw, raw_transform, raw_crs, source = read_mask_window(bbox)
    mask = align_mask_to_dem(raw, raw_transform, raw_crs, dem_shape, dem_transform, dem_crs)
    local_water = (mask == 1) | (mask == 3)
    if np.any(mask == 1):
        tidal = ndi.binary_propagation(mask == 1, structure=STRUCTURE_8, mask=local_water)
        return mask, tidal, {
            "marine_seed_status": "resolved_local_ocean",
            "marine_context_width_km": 10.0,
            "marine_context_source": source,
            "marine_context_ocean_cells": int((mask == 1).sum()),
            "marine_context_river_cells": int((mask == 3).sum()),
        }

    if np.any(mask == 3):
        for width_km in MARINE_CONTEXT_WIDTHS_KM:
            context_bbox = fixed_km_bbox(lon, lat, width_km)
            context, context_transform, context_crs, context_source = read_mask_window(context_bbox)
            context_ocean = context == 1
            context_river = context == 3
            if not np.any(context_ocean):
                continue
            context_tidal = ndi.binary_propagation(
                context_ocean,
                structure=STRUCTURE_8,
                mask=context_ocean | context_river,
            )
            tidal = align_binary_to_dem(
                context_tidal,
                context_transform,
                context_crs,
                dem_shape,
                dem_transform,
                dem_crs,
            ) & local_water
            if np.any(tidal):
                return mask, tidal, {
                    "marine_seed_status": "resolved_context_ocean_connected_river",
                    "marine_context_width_km": width_km,
                    "marine_context_source": context_source,
                    "marine_context_ocean_cells": int(context_ocean.sum()),
                    "marine_context_river_cells": int(context_river.sum()),
                }

    return mask, np.zeros(dem_shape, dtype=bool), {
        "marine_seed_status": "unresolved_no_ocean_connected_water_evidence",
        "marine_context_width_km": max(MARINE_CONTEXT_WIDTHS_KM),
        "marine_context_source": source,
        "marine_context_ocean_cells": 0,
        "marine_context_river_cells": int((mask == 3).sum()),
    }


def mask_aware_layers(
    elev: np.ndarray,
    valid: np.ndarray,
    mask: np.ndarray,
    eta: float,
    tidal_water: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Return low and connected layers using official mask water classes."""
    ocean = mask == 1
    river = mask == 3
    lake = mask == 2
    clipped = mask == 255
    outside_support = mask == MASK_OUTSIDE_SUPPORT
    land = mask == 0

    # River is treated as tidal seed only if it connects to ocean through the
    # ocean/river water network. Lakes are deliberately excluded.
    if tidal_water is None:
        water_network = ocean | river
        tidal_water = ndi.binary_propagation(ocean, structure=STRUCTURE_8, mask=water_network)

    usable_valid = valid & land
    low = usable_valid & np.isfinite(elev) & (elev <= eta)
    passable = low | tidal_water
    reachable = ndi.binary_propagation(tidal_water, structure=STRUCTURE_8, mask=passable)
    connected = reachable & low
    return {
        "low": low,
        "connected": connected,
        "tidal_water": tidal_water,
        "ocean": ocean,
        "river": river,
        "lake": lake,
        "clipped": clipped,
        "outside_support": outside_support,
        "land": land,
    }


def compute_station(row: pd.Series) -> tuple[dict[str, object], dict[str, object]]:
    bbox = (
        float(row["bbox_west"]),
        float(row["bbox_south"]),
        float(row["bbox_east"]),
        float(row["bbox_north"]),
    )
    lon2d, lat2d, elev, dem_source, dem_meta, dem_tiles = read_dem_window_fast(bbox)
    valid = valid_mask(elev)
    mask, tidal_water, seed_audit = resolve_marine_seed(
        float(row["lon"]),
        float(row["lat"]),
        bbox,
        elev.shape,
        dem_meta["transform"],
        dem_meta["crs"],
    )
    mask_source = str(seed_audit["marine_context_source"])
    area = cell_area_km2(lon2d, lat2d)
    ocean = mask == 1
    river = mask == 3
    lake = mask == 2
    clipped = mask == 255
    outside_support = mask == MASK_OUTSIDE_SUPPORT
    land = mask == 0
    tidal_river = tidal_water & river
    seed_resolved = str(seed_audit["marine_seed_status"]).startswith("resolved_")
    usable_valid = valid & land
    lowland = usable_valid & np.isfinite(elev) & (elev <= LOWLAND_MAX_M)
    denom_area = sum_area(area, lowland)
    # Class 255 records clipped product support rather than a finite observed
    # elevation. Keep it in the audit counts, but exclude it from every areal
    # denominator and terrain-response layer.
    reference_land = usable_valid
    reference_land_area = sum_area(area, reference_land)
    window_area = sum_area(area, np.ones(valid.shape, dtype=bool))

    metrics: dict[str, object] = {
        "station_id": row["station_id"],
        "station": row["station"],
        "lat": row["lat"],
        "lon": row["lon"],
        "coast_rp_rp10_m": row["coast_rp_rp10_m"],
        "match_dist_km": row.get("match_dist_km", np.nan),
        "passes_primary_match_le6km": bool(
            np.isfinite(row.get("match_dist_km", np.nan))
            and float(row.get("match_dist_km", np.nan)) <= MAX_PRIMARY_COAST_MATCH_KM
        ),
        "archive_available": row.get("archive_available", False),
        "passes_years_ge25": row.get("passes_years_ge25", False),
        "passes_corr_ge055": row.get("passes_corr_ge055", False),
        "selected_base_30": row.get("selected_base_30", False),
        "window_width_km": row["window_width_km"],
        "bbox_west": bbox[0],
        "bbox_south": bbox[1],
        "bbox_east": bbox[2],
        "bbox_north": bbox[3],
        "terrain_source": dem_source,
        "terrain_tiles": ";".join(dem_tiles),
        "mask_source": mask_source,
        "official_mask_classes_used": True,
        "deltadtm_release": "v1.1.1",
        "deltadtm_vertical_reference": "EGM2008",
        "deltadtm_release_cap_m": 30.0,
        "marine_seed_rule": "ocean class 1 plus river class 3 cells connected to ocean in an adaptive context; lake class 2 and 255 clipped cells excluded",
        "marine_seed_resolved": seed_resolved,
        **seed_audit,
        "mask_lowland_area_km2": denom_area,
        "mask_reference_land_area_km2": reference_land_area,
        "mask_lowland_cells": int(lowland.sum()),
        "mask_tidal_water_cells": int(tidal_water.sum()),
        "mask_tidal_river_cells": int(tidal_river.sum()),
        "mask_ocean_cells": int(ocean.sum()),
        "mask_river_cells": int(river.sum()),
        "mask_lake_cells": int(lake.sum()),
        "mask_clipped_255_cells": int(clipped.sum()),
        "mask_outside_support_cells": int(outside_support.sum()),
        "mask_land_cells": int(land.sum()),
        "mask_ocean_area_km2": sum_area(area, ocean),
        "mask_river_area_km2": sum_area(area, river),
        "mask_lake_area_km2": sum_area(area, lake),
        "mask_clipped_255_area_km2": sum_area(area, clipped),
        "mask_outside_support_area_km2": sum_area(area, outside_support),
        "mask_land_area_km2": sum_area(area, land),
    }
    counts: dict[str, object] = {
        "station_id": row["station_id"],
        "station": row["station"],
        "mask_source": mask_source,
        "marine_seed_resolved": seed_resolved,
        **seed_audit,
        "window_area_km2": window_area,
        "valid_area_km2": sum_area(area, valid),
        "mask_lowland_area_km2": denom_area,
        "mask_reference_land_area_km2": reference_land_area,
    }
    for value, label in MASK_CLASS_NAMES.items():
        class_mask = mask == value
        counts[f"{label}_cells"] = int(class_mask.sum())
        counts[f"{label}_area_km2"] = sum_area(area, class_mask)

    if denom_area <= 0 or reference_land_area <= 0:
        for level in LEVELS_M:
            prefix = f"{level:g}m"
            metrics[f"mask_connected_{prefix}_lowland_pct"] = np.nan
            metrics[f"mask_all_below_{prefix}_lowland_pct"] = np.nan
            metrics[f"mask_unconnected_{prefix}_lowland_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_area_km2"] = np.nan
            metrics[f"mask_all_below_{prefix}_area_km2"] = np.nan
            metrics[f"mask_unconnected_{prefix}_area_km2"] = np.nan
            metrics[f"mask_below_{prefix}_reference_land_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_conditional_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_reference_land_pct"] = np.nan
        return metrics, counts

    for level in LEVELS_M:
        layers = mask_aware_layers(elev, valid, mask, level, tidal_water=tidal_water)
        low = layers["low"] & lowland
        connected = layers["connected"] & lowland
        below_area = sum_area(area, low)
        prefix = f"{level:g}m"
        metrics[f"mask_all_below_{prefix}_lowland_pct"] = 100.0 * below_area / denom_area
        metrics[f"mask_all_below_{prefix}_area_km2"] = below_area
        metrics[f"mask_below_{prefix}_reference_land_pct"] = 100.0 * below_area / reference_land_area
        if seed_resolved:
            conn_area = sum_area(area, connected)
            metrics[f"mask_connected_{prefix}_lowland_pct"] = 100.0 * conn_area / denom_area
            metrics[f"mask_unconnected_{prefix}_lowland_pct"] = 100.0 * max(below_area - conn_area, 0.0) / denom_area
            metrics[f"mask_connected_{prefix}_area_km2"] = conn_area
            metrics[f"mask_unconnected_{prefix}_area_km2"] = max(below_area - conn_area, 0.0)
            metrics[f"mask_connected_{prefix}_window_pct"] = 100.0 * conn_area / window_area if window_area else np.nan
            metrics[f"mask_connected_{prefix}_conditional_pct"] = (
                100.0 * conn_area / below_area if below_area else np.nan
            )
            metrics[f"mask_connected_{prefix}_reference_land_pct"] = (
                100.0 * conn_area / reference_land_area
            )
        else:
            # Lack of a marine seed is missing connectivity evidence, not proof
            # that every below-threshold cell is unconnected.
            metrics[f"mask_connected_{prefix}_lowland_pct"] = np.nan
            metrics[f"mask_unconnected_{prefix}_lowland_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_area_km2"] = np.nan
            metrics[f"mask_unconnected_{prefix}_area_km2"] = np.nan
            metrics[f"mask_connected_{prefix}_window_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_conditional_pct"] = np.nan
            metrics[f"mask_connected_{prefix}_reference_land_pct"] = np.nan
    return metrics, counts


def add_proxy_comparison(mask_df: pd.DataFrame, proxy_df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "station_id",
        "connected_2m_lowland_pct",
        "connected_2m_area_km2",
        "all_below_2m_lowland_pct",
        "all_below_2m_area_km2",
        "unconnected_2m_lowland_pct",
        "unconnected_2m_area_km2",
    ]
    merged = mask_df.merge(proxy_df[keep], on="station_id", how="left", suffixes=("", "_proxy"))
    merged["proxy_minus_mask_connected_2m_lowland_pct"] = (
        merged["connected_2m_lowland_pct"] - merged["mask_connected_2m_lowland_pct"]
    )
    merged["proxy_minus_mask_connected_2m_area_km2"] = (
        merged["connected_2m_area_km2"] - merged["mask_connected_2m_area_km2"]
    )
    return merged


def coastal_sector(row: pd.Series) -> str:
    """Coarse geographic blocks used only for spatial block resampling."""
    lon = float(row["lon"])
    lat = float(row["lat"])
    if lon < -5.0:
        return "Atlantic-Celtic"
    if lon < -1.0 and lat < 52.0:
        return "western-English-Channel"
    if lon < 2.5 and lat >= 52.0:
        return "British-North-Sea"
    if lon < 3.5:
        return "eastern-Channel-southern-North-Sea"
    if lon < 8.0:
        return "Dutch-German-Bight"
    return "Denmark-Norway"


def sector_block_bootstrap_assoc(
    frame: pd.DataFrame,
    sample: str,
    terrain_col: str,
    water_col: str = "coast_rp_rp10_m",
    n_boot: int = 2_000,
    seed: int = 20260815,
) -> dict[str, object]:
    """Resample coastal sectors, preserving within-sector station clustering."""
    work = frame.dropna(subset=[water_col, terrain_col, "lon", "lat"]).copy()
    work["coastal_sector"] = work.apply(coastal_sector, axis=1)
    sectors = sorted(work["coastal_sector"].unique())
    observed_s = float(work[water_col].corr(work[terrain_col], method="spearman"))
    observed_k = float(work[water_col].corr(work[terrain_col], method="kendall"))
    rng = np.random.default_rng(seed)
    s_boot = np.full(n_boot, np.nan, dtype=float)
    k_boot = np.full(n_boot, np.nan, dtype=float)
    groups = {
        sector: (
            work.loc[work["coastal_sector"].eq(sector), water_col].to_numpy(dtype=float),
            work.loc[work["coastal_sector"].eq(sector), terrain_col].to_numpy(dtype=float),
        )
        for sector in sectors
    }
    for i in range(n_boot):
        sampled = rng.choice(sectors, size=len(sectors), replace=True)
        boot_water = np.concatenate([groups[sector][0] for sector in sampled])
        boot_terrain = np.concatenate([groups[sector][1] for sector in sampled])
        if np.unique(boot_water).size > 1 and np.unique(boot_terrain).size > 1:
            s_boot[i] = float(stats.spearmanr(boot_water, boot_terrain).statistic)
            k_boot[i] = float(stats.kendalltau(boot_water, boot_terrain).statistic)
    return {
        "sample": sample,
        "terrain_metric": terrain_col,
        "n_sites": int(len(work)),
        "n_coastal_sectors": int(len(sectors)),
        "coastal_sectors": ";".join(sectors),
        "n_bootstrap": int(n_boot),
        "spearman": observed_s,
        "spearman_block_p025": float(np.nanpercentile(s_boot, 2.5)),
        "spearman_block_p500": float(np.nanpercentile(s_boot, 50.0)),
        "spearman_block_p975": float(np.nanpercentile(s_boot, 97.5)),
        "kendall": observed_k,
        "kendall_block_p025": float(np.nanpercentile(k_boot, 2.5)),
        "kendall_block_p500": float(np.nanpercentile(k_boot, 50.0)),
        "kendall_block_p975": float(np.nanpercentile(k_boot, 97.5)),
        "interpretation": "geographic block-resampling interval; not a measurement-error interval",
    }


def build_rank_tables(mask_df: pd.DataFrame) -> None:
    resolved = mask_df[mask_df["marine_seed_resolved"].eq(True)].copy()
    primary = resolved[
        resolved["match_dist_km"].notna()
        & resolved["match_dist_km"].le(MAX_PRIMARY_COAST_MATCH_KM)
    ].copy()
    subsets = {
        "primary resolved mask-aware match<=6km": primary,
        "all resolved mask-aware distance-unrestricted sensitivity": resolved,
        "GSSR-qualified primary mask-aware": primary[
            primary["archive_available"].eq(True)
            & primary["passes_years_ge25"].eq(True)
            & primary["passes_corr_ge055"].eq(True)
        ].copy(),
        "baseline 30-station primary sensitivity": primary[primary["selected_base_30"].eq(True)].copy(),
    }
    rank_rows = []
    overlap_tables = []
    assoc_rows = []
    block_rows = []
    for sample, frame in subsets.items():
        frame = frame.dropna(
            subset=["coast_rp_rp10_m", "mask_connected_2m_reference_land_pct", "mask_connected_2m_area_km2"]
        ).copy()
        for metric in [
            "mask_connected_2m_reference_land_pct",
            "mask_below_2m_reference_land_pct",
            "mask_connected_2m_conditional_pct",
            "mask_connected_2m_area_km2",
        ]:
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
            overlap_tables.append(top_overlap_curve(frame, sample, metric, seed=20260716 + len(overlap_tables)))
            assoc_rows.append(permutation_assoc(frame, sample, metric, seed=20260726 + len(assoc_rows)))
            if sample == "primary resolved mask-aware match<=6km":
                block_rows.append(
                    sector_block_bootstrap_assoc(
                        frame,
                        sample,
                        metric,
                        seed=20260815 + len(block_rows),
                    )
                )
    rank_df = pd.DataFrame(rank_rows)
    rank_df.to_csv(FIG_SOURCE / "Primary_rank_metrics_by_terrain_component.csv", index=False)
    # Compatibility alias; current rows use the decomposed v1.1 metrics.
    rank_df.to_csv(FIG_SOURCE / "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv", index=False)
    pd.concat(overlap_tables, ignore_index=True).to_csv(
        FIG_SOURCE / "Fig6_mask_aware_topk_overlap_null_envelope.csv", index=False
    )
    pd.DataFrame(assoc_rows).to_csv(FIG_SOURCE / "Fig6_mask_aware_two_sided_permutation_association.csv", index=False)
    pd.DataFrame(block_rows).to_csv(FIG_SOURCE / "Fig6_mask_aware_sector_block_bootstrap.csv", index=False)


def write_balanced_archetype_table(mask_df: pd.DataFrame) -> None:
    """Select map examples with a declared rank rule, never station hard-coding."""
    subset = mask_df[
        mask_df["marine_seed_resolved"].eq(True)
        & mask_df["match_dist_km"].le(MAX_PRIMARY_COAST_MATCH_KM)
    ].dropna(subset=["coast_rp_rp10_m", "mask_connected_2m_reference_land_pct"]).copy()
    subset["water_rank"] = subset["coast_rp_rp10_m"].rank(ascending=False, method="min").astype(int)
    subset["terrain_rank"] = subset["mask_connected_2m_reference_land_pct"].rank(ascending=False, method="min").astype(int)
    subset["terrain_minus_water_rank"] = subset["terrain_rank"] - subset["water_rank"]
    subset["water_minus_terrain_rank"] = subset["water_rank"] - subset["terrain_rank"]
    top_n = max(1, math.ceil(0.2 * len(subset)))
    subset["water_top20"] = subset["water_rank"].le(top_n)
    subset["terrain_top20"] = subset["terrain_rank"].le(top_n)
    # The minimum mapped area is a legibility constraint, recorded explicitly;
    # it is not a scientific threshold or a stability claim.
    readable = subset[subset["mask_connected_2m_area_km2"].ge(0.05)].copy()
    candidate_rules = [
        (
            "aligned high storm-tide / high connected-terrain",
            readable[readable["water_top20"] & readable["terrain_top20"]].sort_values(
                ["mask_connected_2m_area_km2", "station_id"], ascending=[False, True]
            ),
            "both metrics in top 20%; largest connected area among map-legible candidates",
        ),
        (
            "high storm-tide / lower connected-terrain",
            readable[readable["water_top20"] & ~readable["terrain_top20"]].sort_values(
                ["terrain_minus_water_rank", "station_id"], ascending=[False, True]
            ),
            "storm tide in top 20%, terrain outside top 20%; largest positive rank displacement",
        ),
        (
            "lower storm-tide / high connected-terrain",
            readable[~readable["water_top20"] & readable["terrain_top20"]].sort_values(
                ["water_minus_terrain_rank", "station_id"], ascending=[False, True]
            ),
            "terrain in top 20%, storm tide outside top 20%; largest positive reverse displacement",
        ),
    ]
    rows: list[dict[str, object]] = []
    for archetype, candidates, rule in candidate_rules:
        if candidates.empty:
            raise RuntimeError(f"No auditable map candidate for archetype: {archetype}")
        r = candidates.iloc[0]
        rows.append(
            {
                "archetype": archetype,
                "selection_rule": rule,
                "minimum_connected_area_for_map_legibility_km2": 0.05,
                "station_id": r["station_id"],
                "station": r["station"],
                "coast_rp_rp10_m": r["coast_rp_rp10_m"],
                "connected_2m_reference_land_pct": r["mask_connected_2m_reference_land_pct"],
                "below_2m_reference_land_pct": r["mask_below_2m_reference_land_pct"],
                "conditional_connectivity_2m_pct": r["mask_connected_2m_conditional_pct"],
                "connected_2m_area_km2": r["mask_connected_2m_area_km2"],
                "coastal_lowland_area_km2": r["mask_lowland_area_km2"],
                "water_rank": r["water_rank"],
                "terrain_rank": r["terrain_rank"],
                "terrain_minus_water_rank": r["terrain_rank"] - r["water_rank"],
                "water_minus_terrain_rank": r["water_rank"] - r["terrain_rank"],
                "match_dist_km": r["match_dist_km"],
                "marine_seed_status": r["marine_seed_status"],
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig6_archetype_map_selection.csv", index=False)
    # Preserve the earlier filename as an exact compatibility alias so that
    # audit packages cannot retain a contradictory archetype selection table.
    out.to_csv(FIG_SOURCE / "Fig6_mask_aware_archetype_map_selection.csv", index=False)


def write_mask_audit(mask_df: pd.DataFrame) -> None:
    audit = {
        "official_mask_tiles_zip_present": True,
        "official_mask_tiles_zip_path": str(MASK_ZIP.relative_to(ROOT)),
        "official_mask_tiles_zip_size_bytes": MASK_ZIP.stat().st_size,
        "official_mask_tiles_zip_md5_expected": MASK_EXPECTED_MD5,
        "official_mask_tiles_zip_md5_verified": True,
        "official_mask_classes_used": True,
        "mask_aware_metrics_table": "data/figure_source/Fig6_mask_aware_terrain_area_metrics.csv",
        "mask_class_counts_table": "data/figure_source/Fig6_mask_class_counts.csv",
        "deltadtm_release": "v1.1.1",
        "deltadtm_release_cap_m": 30.0,
        "mask_outside_support_fill_value": int(MASK_OUTSIDE_SUPPORT),
        "marine_seed_rule": "ocean class 1 plus river class 3 connected to ocean in an adaptive 25-200 km mask context; classes 2, 254 and 255 excluded from land denominators",
        "unresolved_station_count": int((~mask_df["marine_seed_resolved"].eq(True)).sum()),
        "primary_coast_rp_match_max_km": MAX_PRIMARY_COAST_MATCH_KM,
        "primary_resolved_station_count": int(
            (mask_df["marine_seed_resolved"].eq(True) & mask_df["match_dist_km"].le(MAX_PRIMARY_COAST_MATCH_KM)).sum()
        ),
        "boundary_proxy_status": "retained as sensitivity comparator, not the only implemented connectivity path",
    }
    pd.DataFrame([audit]).to_csv(FIG_SOURCE / "Fig6_deltadtm_mask_seed_audit.csv", index=False)


def main() -> int:
    ensure_mask_zip()
    proxy = pd.read_csv(FIXED_METRICS)
    rows: list[dict[str, object]] = []
    counts: list[dict[str, object]] = []
    for idx, (_, row) in enumerate(proxy.iterrows(), start=1):
        print(f"[{idx}/{len(proxy)}] mask-aware terrain {row['station_id']}", flush=True)
        metrics, class_counts = compute_station(row)
        rows.append(metrics)
        counts.append(class_counts)
    mask_df = pd.DataFrame(rows)
    mask_df = add_proxy_comparison(mask_df, proxy)
    count_df = pd.DataFrame(counts)
    mask_df.to_csv(FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv", index=False)
    count_df.to_csv(FIG_SOURCE / "Fig6_mask_class_counts.csv", index=False)
    build_rank_tables(mask_df)
    write_balanced_archetype_table(mask_df)

    write_mask_audit(mask_df)
    print("Wrote mask-aware terrain diagnostics")
    print(mask_df[[
        "station_id",
        "mask_connected_2m_reference_land_pct",
        "mask_below_2m_reference_land_pct",
        "mask_connected_2m_conditional_pct",
        "connected_2m_lowland_pct",
        "proxy_minus_mask_connected_2m_lowland_pct",
        "mask_connected_2m_area_km2",
        "connected_2m_area_km2",
    ]].head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

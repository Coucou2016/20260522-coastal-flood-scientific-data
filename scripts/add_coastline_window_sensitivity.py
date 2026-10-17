#!/usr/bin/env python3
"""Compare square windows with a mask-derived coastline-oriented landward strip."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "scripts", ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from add_advanced_terrain_rank_diagnostics import cell_area_km2, fixed_km_bbox, read_dem_window_fast  # noqa: E402
from add_mask_aware_terrain_diagnostics import resolve_marine_seed  # noqa: E402
from coastal_screening.spatial_blocks import attach_spatial_blocks  # noqa: E402
from coastal_screening.statistics import deterministic_top_k  # noqa: E402
from inundation_sensitivity import valid_mask  # noqa: E402
from rebuild_frozen_primary_analysis import classify  # noqa: E402


SOURCE = ROOT / "data" / "figure_source"
BLOCK_CONFIG = ROOT / "config" / "coastal_spatial_blocks_v2.csv"
METRICS = ("connected_reference_land_pct", "connected_area_km2", "below_reference_land_pct")


def oriented_landward_support(
    lon2d: np.ndarray,
    lat2d: np.ndarray,
    mask: np.ndarray,
    tidal_water: np.ndarray,
    station_lon: float,
    station_lat: float,
) -> tuple[np.ndarray, float, str]:
    """Build a 10 km alongshore by 5 km landward strip from mask geometry."""
    x = (lon2d - station_lon) * 111.320 * math.cos(math.radians(station_lat))
    y = (lat2d - station_lat) * 110.574
    land = mask == 0
    shoreline = land & ndi.binary_dilation(tidal_water, structure=ndi.generate_binary_structure(2, 1))
    if shoreline.sum() < 3:
        raise RuntimeError("Insufficient ocean-connected shoreline cells for oriented support")
    shoreline_points = np.column_stack([x[shoreline], y[shoreline]])
    nearest_index = int(np.argmin(np.sum(shoreline_points**2, axis=1)))
    origin = shoreline_points[nearest_index]
    distances = np.sqrt(np.sum((shoreline_points - origin) ** 2, axis=1))
    local = shoreline_points[distances <= 4.0]
    if len(local) < 5:
        local = shoreline_points
    covariance = np.cov((local - local.mean(axis=0)).T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    tangent = eigenvectors[:, int(np.argmax(eigenvalues))]
    normal = np.array([-tangent[1], tangent[0]])
    land_points = np.column_stack([x[land], y[land]])
    local_land = land_points[np.sqrt(np.sum((land_points - origin) ** 2, axis=1)) <= 5.0]
    if len(local_land) == 0:
        raise RuntimeError("No local land cells for landward orientation")
    if np.dot(np.median(local_land, axis=0) - origin, normal) < 0:
        normal *= -1.0
    dx = x - origin[0]
    dy = y - origin[1]
    along = dx * tangent[0] + dy * tangent[1]
    landward = dx * normal[0] + dy * normal[1]
    support = (np.abs(along) <= 5.0) & (landward >= 0.0) & (landward <= 5.0)
    azimuth = (math.degrees(math.atan2(tangent[0], tangent[1])) + 180.0) % 180.0
    return support, azimuth, "mask-derived shoreline PCA within 4 km; nearest shoreline origin"


def main() -> int:
    primary = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv"),
        BLOCK_CONFIG,
    )
    rows: list[dict[str, object]] = []
    for index, (_, station) in enumerate(primary.iterrows(), start=1):
        print(f"[{index}/{len(primary)}] coastline window {station['station_id']}", flush=True)
        bbox = fixed_km_bbox(float(station["lon"]), float(station["lat"]), 12.0)
        lon2d, lat2d, elevation, _, metadata, _ = read_dem_window_fast(bbox)
        valid = valid_mask(elevation)
        mask, tidal_water, seed_audit = resolve_marine_seed(
            float(station["lon"]),
            float(station["lat"]),
            bbox,
            elevation.shape,
            metadata["transform"],
            metadata["crs"],
            water_neighbours=8,
        )
        if not str(seed_audit["marine_seed_status"]).startswith("resolved_"):
            raise RuntimeError(f"Unresolved marine seed for {station['station_id']}")
        support, azimuth, orientation_method = oriented_landward_support(
            lon2d,
            lat2d,
            mask,
            tidal_water,
            float(station["lon"]),
            float(station["lat"]),
        )
        area = cell_area_km2(lon2d, lat2d)
        strip = classify(
            elevation,
            valid & support,
            mask,
            area,
            tidal_water,
            eta_m=2.0,
            neighbours=4,
        )
        rows.append(
            {
                "station_id": station["station_id"],
                "station": station["station"],
                "lat": station["lat"],
                "lon": station["lon"],
                "coast_rp_rp10_m": station["coast_rp_rp10_m"],
                "window_geometry": "10km-alongshore-by-5km-landward",
                "shoreline_tangent_azimuth_deg_mod180": azimuth,
                "orientation_method": orientation_method,
                "water_neighbours": 8,
                "land_neighbours": 4,
                **strip,
            }
        )
    oriented = pd.DataFrame(rows)
    oriented.to_csv(SOURCE / "Coastline_oriented_window_68stations.csv", index=False)
    baseline = primary.set_index("station_id")
    comparison = oriented.set_index("station_id").loc[baseline.index]
    summary: list[dict[str, object]] = []
    ids = baseline.index.to_numpy(str)
    k = int(math.ceil(0.20 * len(ids)))
    for metric in METRICS:
        square = baseline[metric].to_numpy(float)
        coast = comparison[metric].to_numpy(float)
        square_top = set(ids[deterministic_top_k(square, ids, k)])
        coast_top = set(ids[deterministic_top_k(coast, ids, k)])
        summary.append(
            {
                "terrain_metric": metric,
                "n_sites": len(ids),
                "terrain_rank_spearman_oriented_vs_square": float(stats.spearmanr(square, coast).statistic),
                "water_vs_oriented_spearman": float(stats.spearmanr(comparison["coast_rp_rp10_m"], coast).statistic),
                "water_vs_square_spearman": float(stats.spearmanr(baseline["coast_rp_rp10_m"], square).statistic),
                "top20_n": k,
                "top20_overlap_oriented_vs_square": len(square_top & coast_top),
                "top20_membership_changes": len(square_top ^ coast_top),
                "interpretation": "mask-derived window-geometry sensitivity, not an alternative flood model",
            }
        )
    pd.DataFrame(summary).to_csv(SOURCE / "Coastline_window_sensitivity_summary.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compute threshold-integrated terrain metrics from 0 to 3 m EGM2008."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "scripts", ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from add_advanced_terrain_rank_diagnostics import (  # noqa: E402
    cell_area_km2,
    fixed_km_bbox,
    read_dem_window_fast,
)
from add_mask_aware_terrain_diagnostics import resolve_marine_seed  # noqa: E402
from coastal_screening.spatial_blocks import attach_spatial_blocks  # noqa: E402
from inundation_sensitivity import valid_mask  # noqa: E402
from rebuild_frozen_primary_analysis import classify  # noqa: E402


SOURCE = ROOT / "data" / "figure_source"
BLOCK_CONFIG = ROOT / "config" / "coastal_spatial_blocks_v2.csv"
LEVELS = np.round(np.arange(0.0, 3.0001, 0.25), 2)


def threshold_average(values: np.ndarray, levels: np.ndarray) -> float:
    """Return a trapezoidal average over a positive threshold interval."""
    span = float(levels[-1] - levels[0])
    if span <= 0:
        raise ValueError("Threshold levels must span a positive interval")
    return float(np.trapz(values, levels) / span)


def main() -> int:
    primary = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv"),
        BLOCK_CONFIG,
    )
    curve_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for index, (_, station) in enumerate(primary.iterrows(), start=1):
        print(f"[{index}/{len(primary)}] threshold curve {station['station_id']}", flush=True)
        bbox = fixed_km_bbox(float(station["lon"]), float(station["lat"]), 10.0)
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
            raise RuntimeError(f"Unresolved primary marine seed for {station['station_id']}")
        area = cell_area_km2(lon2d, lat2d)
        station_curves: list[dict[str, float]] = []
        for level in LEVELS:
            result = classify(
                elevation,
                valid,
                mask,
                area,
                tidal_water,
                float(level),
                neighbours=4,
            )
            station_curves.append(result)
            curve_rows.append(
                {
                    "station_id": station["station_id"],
                    "station": station["station"],
                    "eta_m_egm2008": level,
                    "water_neighbours": 8,
                    "land_neighbours": 4,
                    **result,
                }
            )
        connected_share = np.array([row["connected_reference_land_pct"] for row in station_curves])
        connected_area = np.array([row["connected_area_km2"] for row in station_curves])
        below_share = np.array([row["below_reference_land_pct"] for row in station_curves])
        summary_rows.append(
            {
                "station_id": station["station_id"],
                "station": station["station"],
                "lat": station["lat"],
                "lon": station["lon"],
                "coast_rp_rp10_m": station["coast_rp_rp10_m"],
                "connected_share_auc_0_3m_pct": threshold_average(connected_share, LEVELS),
                "connected_area_auc_0_3m_km2": threshold_average(connected_area, LEVELS),
                "below_share_auc_0_3m_pct": threshold_average(below_share, LEVELS),
                "threshold_min_m_egm2008": float(LEVELS[0]),
                "threshold_max_m_egm2008": float(LEVELS[-1]),
                "threshold_step_m": 0.25,
                "water_neighbours": 8,
                "land_neighbours": 4,
            }
        )
    curves = pd.DataFrame(curve_rows)
    summary = pd.DataFrame(summary_rows)
    curves.to_csv(SOURCE / "Threshold_response_0_3m_68stations.csv", index=False)
    summary.to_csv(SOURCE / "Threshold_integrated_terrain_metrics_68stations.csv", index=False)
    associations = []
    for metric in (
        "connected_share_auc_0_3m_pct",
        "connected_area_auc_0_3m_km2",
        "below_share_auc_0_3m_pct",
    ):
        associations.append(
            {
                "terrain_metric": metric,
                "n_sites": len(summary),
                "spearman": float(stats.spearmanr(summary["coast_rp_rp10_m"], summary[metric]).statistic),
                "kendall": float(stats.kendalltau(summary["coast_rp_rp10_m"], summary[metric]).statistic),
                "interpretation": "threshold-integrated standardized EGM2008 terrain screen; not a flood probability",
            }
        )
    pd.DataFrame(associations).to_csv(SOURCE / "Threshold_integrated_associations.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

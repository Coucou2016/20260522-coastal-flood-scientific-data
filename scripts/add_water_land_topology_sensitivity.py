#!/usr/bin/env python3
"""Evaluate all 4/8-neighbour water-seed and land-graph combinations."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
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
METRICS = ("connected_reference_land_pct", "connected_area_km2", "conditional_connectivity_pct")


def main() -> int:
    primary = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv"),
        BLOCK_CONFIG,
    )
    rows: list[dict[str, object]] = []
    for index, (_, station) in enumerate(primary.iterrows(), start=1):
        print(f"[{index}/{len(primary)}] topology {station['station_id']}", flush=True)
        bbox = fixed_km_bbox(float(station["lon"]), float(station["lat"]), 10.0)
        lon2d, lat2d, elevation, _, metadata, _ = read_dem_window_fast(bbox)
        valid = valid_mask(elevation)
        area = cell_area_km2(lon2d, lat2d)
        for water_neighbours in (4, 8):
            mask, tidal_water, seed_audit = resolve_marine_seed(
                float(station["lon"]),
                float(station["lat"]),
                bbox,
                elevation.shape,
                metadata["transform"],
                metadata["crs"],
                water_neighbours=water_neighbours,
            )
            if not str(seed_audit["marine_seed_status"]).startswith("resolved_"):
                raise RuntimeError(f"Unresolved marine seed for {station['station_id']}")
            for land_neighbours in (4, 8):
                result = classify(
                    elevation,
                    valid,
                    mask,
                    area,
                    tidal_water,
                    eta_m=2.0,
                    neighbours=land_neighbours,
                )
                rows.append(
                    {
                        "station_id": station["station_id"],
                        "station": station["station"],
                        "coast_rp_rp10_m": station["coast_rp_rp10_m"],
                        "water_neighbours": water_neighbours,
                        "land_neighbours": land_neighbours,
                        **result,
                    }
                )
    detail = pd.DataFrame(rows)
    detail.to_csv(SOURCE / "Water_land_topology_sensitivity_68stations.csv", index=False)
    baseline = detail[
        detail["water_neighbours"].eq(8) & detail["land_neighbours"].eq(4)
    ].set_index("station_id")
    summary: list[dict[str, object]] = []
    for (water_neighbours, land_neighbours), group in detail.groupby(
        ["water_neighbours", "land_neighbours"], sort=True
    ):
        group = group.set_index("station_id").loc[baseline.index]
        n = len(group)
        k = int(math.ceil(0.2 * n))
        ids = group.index.to_numpy(str)
        for metric in METRICS:
            values = group[metric].to_numpy(float)
            baseline_values = baseline[metric].to_numpy(float)
            selected = set(ids[deterministic_top_k(values, ids, k)])
            baseline_selected = set(ids[deterministic_top_k(baseline_values, ids, k)])
            summary.append(
                {
                    "water_neighbours": water_neighbours,
                    "land_neighbours": land_neighbours,
                    "terrain_metric": metric,
                    "n_sites": n,
                    "water_vs_terrain_spearman": float(stats.spearmanr(group["coast_rp_rp10_m"], values).statistic),
                    "terrain_rank_spearman_vs_primary_8water_4land": float(stats.spearmanr(baseline_values, values).statistic),
                    "top20_n": k,
                    "top20_overlap_with_primary": len(selected & baseline_selected),
                    "top20_membership_changes": len(selected ^ baseline_selected),
                }
            )
    pd.DataFrame(summary).to_csv(SOURCE / "Water_land_topology_summary.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

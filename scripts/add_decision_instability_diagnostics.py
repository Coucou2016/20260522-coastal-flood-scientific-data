#!/usr/bin/env python3
"""Quantify site-selection stability across the prespecified terrain grid."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from coastal_screening.spatial_blocks import attach_spatial_blocks  # noqa: E402
from coastal_screening.statistics import deterministic_top_k  # noqa: E402


SOURCE = ROOT / "data" / "figure_source"
BLOCK_CONFIG = ROOT / "config" / "coastal_spatial_blocks_v2.csv"
METRIC = "connected_reference_land_pct"
CONFIG_COLUMNS = [
    "window_width_km",
    "eta_m",
    "neighbours",
    "seed_rule",
    "elevation_offset_m",
]


def descending_rank(values: np.ndarray, station_ids: np.ndarray) -> np.ndarray:
    order = deterministic_top_k(values, station_ids, len(values))
    ranks = np.empty(len(values), dtype=int)
    ranks[order] = np.arange(1, len(values) + 1)
    return ranks


def priority_label(water_top: bool, terrain_top: bool) -> str:
    if water_top and terrain_top:
        return "dual-priority"
    if water_top:
        return "water-priority-only"
    if terrain_top:
        return "terrain-priority-only"
    return "neither-top20"


def pareto_front(water: np.ndarray, terrain: np.ndarray) -> np.ndarray:
    dominated = np.zeros(len(water), dtype=bool)
    for i in range(len(water)):
        dominates = (water >= water[i]) & (terrain >= terrain[i]) & (
            (water > water[i]) | (terrain > terrain[i])
        )
        dominated[i] = bool(np.any(dominates))
    return ~dominated


def main() -> int:
    primary = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv"),
        BLOCK_CONFIG,
    ).sort_values("station_id").reset_index(drop=True)
    detail = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Terrain_robustness_grid_74stations.csv"),
        BLOCK_CONFIG,
    )
    detail = detail[
        detail["station_id"].isin(primary["station_id"])
        & detail["seed_resolved"].eq(True)
        & detail["match_dist_km"].le(6.0)
    ].copy()
    station_ids = primary["station_id"].to_numpy(str)
    water = primary["coast_rp_rp10_m"].to_numpy(float)
    terrain = primary[METRIC].to_numpy(float)
    k = int(math.ceil(0.20 * len(primary)))
    water_top_ids = set(station_ids[deterministic_top_k(water, station_ids, k)])
    terrain_top_ids = set(station_ids[deterministic_top_k(terrain, station_ids, k)])
    primary["water_rank"] = descending_rank(water, station_ids)
    primary["terrain_rank"] = descending_rank(terrain, station_ids)
    primary["terrain_minus_water_rank"] = primary["terrain_rank"] - primary["water_rank"]
    primary["absolute_rank_displacement"] = primary["terrain_minus_water_rank"].abs()
    primary["water_top20"] = primary["station_id"].isin(water_top_ids)
    primary["terrain_top20"] = primary["station_id"].isin(terrain_top_ids)
    primary["priority_class"] = [
        priority_label(w, t) for w, t in zip(primary["water_top20"], primary["terrain_top20"])
    ]
    primary["pareto_nondominated"] = pareto_front(water, terrain)

    selections: list[dict[str, object]] = []
    for config_values, group in detail.groupby(CONFIG_COLUMNS, dropna=False, sort=True):
        group = group.dropna(subset=[METRIC]).sort_values("station_id")
        config_id = "|".join(f"{column}={value}" for column, value in zip(CONFIG_COLUMNS, config_values))
        n = len(group)
        top_n = int(math.ceil(0.20 * n))
        ids = group["station_id"].to_numpy(str)
        selected = set(ids[deterministic_top_k(group[METRIC].to_numpy(float), ids, top_n)])
        for station_id in ids:
            selections.append(
                {
                    "configuration": config_id,
                    "station_id": station_id,
                    "n_eligible_sites": n,
                    "top_n": top_n,
                    "selected_terrain_top20": station_id in selected,
                    **dict(zip(CONFIG_COLUMNS, config_values)),
                }
            )
    selection_frame = pd.DataFrame(selections)
    selection_frame.to_csv(SOURCE / "Terrain_configuration_top20_selections.csv", index=False)
    frequency = (
        selection_frame.groupby("station_id", as_index=False)
        .agg(
            eligible_configurations=("selected_terrain_top20", "size"),
            selected_configurations=("selected_terrain_top20", "sum"),
        )
    )
    frequency["terrain_top20_selection_frequency"] = (
        frequency["selected_configurations"] / frequency["eligible_configurations"]
    )
    primary = primary.merge(frequency, on="station_id", how="left", validate="one_to_one")
    primary["terrain_priority_switch_rate"] = np.where(
        primary["terrain_top20"],
        1.0 - primary["terrain_top20_selection_frequency"],
        primary["terrain_top20_selection_frequency"],
    )

    water_quartile = pd.qcut(primary["water_rank"], 4, labels=["Q1-high", "Q2", "Q3", "Q4-low"])
    terrain_quartile = pd.qcut(primary["terrain_rank"], 4, labels=["Q1-high", "Q2", "Q3", "Q4-low"])
    primary["water_priority_quartile"] = water_quartile.astype(str)
    primary["terrain_priority_quartile"] = terrain_quartile.astype(str)
    transition = pd.crosstab(
        primary["water_priority_quartile"],
        primary["terrain_priority_quartile"],
        margins=True,
    )
    transition.to_csv(SOURCE / "Priority_quartile_transition_matrix.csv")
    primary.to_csv(SOURCE / "Decision_instability_station_metrics.csv", index=False)
    primary[primary["pareto_nondominated"]].to_csv(SOURCE / "Pareto_front_sites.csv", index=False)
    class_counts = primary.groupby("priority_class", as_index=False).size()
    class_counts.to_csv(SOURCE / "Priority_class_counts.csv", index=False)

    summary = {
        "n_sites": len(primary),
        "top20_n": k,
        "top20_overlap": len(water_top_ids & terrain_top_ids),
        "median_absolute_rank_displacement": float(primary["absolute_rank_displacement"].median()),
        "maximum_absolute_rank_displacement": int(primary["absolute_rank_displacement"].max()),
        "median_terrain_top20_selection_frequency": float(primary["terrain_top20_selection_frequency"].median()),
        "stations_always_selected": int(primary["terrain_top20_selection_frequency"].eq(1.0).sum()),
        "stations_never_selected": int(primary["terrain_top20_selection_frequency"].eq(0.0).sum()),
        "pareto_front_sites": int(primary["pareto_nondominated"].sum()),
        "scope": "Decision stability across archived prespecified terrain configurations; no external hazard truth benchmark.",
    }
    (SOURCE / "Screening_decision_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Add subset-selection, rank-discordance, and terrain-screen robustness diagnostics."""

from __future__ import annotations

import math
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_nw_europe_extended_diagnostics import (  # noqa: E402
    CORE_SITE_IDS,
    EUROPE_ZIP,
    FIG_SOURCE,
    GSSR_META,
    TILE_INDEX,
    archive_from_path,
    bbox_for_station,
    display_name,
    ensure_tiles_for_bbox,
    github_archives,
    slug_from_path,
)
from combo1_utils import RAW, haversine_km  # noqa: E402
from inundation_sensitivity import coastal_mask, load_dem, valid_mask  # noqa: E402
from make_cee_refined_figures import (  # noqa: E402
    boundary_ocean_seed,
    flood_connectivity_layers,
    flood_fill,
)


COAST_NC = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
TILES_DIR = RAW / "deltadtm" / "tiles"
BASE_SCREENING = FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv"
CANDIDATE_POOL_SCREENING = FIG_SOURCE / "Fig5_candidate_pool_terrain_screening.csv"

RP_VARS = {
    10: "storm_tide_rp_0010",
    50: "storm_tide_rp_0050",
    100: "storm_tide_rp_0100",
}
ETA_LEVELS = [1.0, 2.0, 3.0]


def load_metadata() -> pd.DataFrame:
    meta = gpd.read_file(GSSR_META)
    meta["lon"] = meta.geometry.x.astype(float)
    meta["lat"] = meta.geometry.y.astype(float)
    meta["station_id"] = meta["path"].map(slug_from_path)
    meta["gssr_archive"] = meta["path"].map(archive_from_path)
    meta["station"] = [display_name(sid, tg) for sid, tg in zip(meta["station_id"], meta["tg"])]
    return pd.DataFrame(meta.drop(columns="geometry"))


def tile_availability_for_bbox(bbox: tuple[float, float, float, float]) -> tuple[bool, str]:
    gdf = gpd.read_file(TILE_INDEX)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    tiles = [str(t) for t in gdf[gdf.intersects(box(*bbox))]["tile"]]
    if not tiles:
        return False, ""
    stems = [Path(tile).stem for tile in tiles]
    local_ok = all(list(TILES_DIR.rglob(f"*{stem}*.tif")) for stem in stems)
    if local_ok:
        return True, ";".join(tiles)
    if EUROPE_ZIP.exists():
        with zipfile.ZipFile(EUROPE_ZIP) as zf:
            members = [Path(m).stem for m in zf.namelist() if m.lower().endswith(".tif")]
        zip_ok = all(any(stem in member for member in members) for stem in stems)
        return bool(zip_ok), ";".join(tiles)
    return False, ";".join(tiles)


def nearest_coastrp_for_rows(rows: pd.DataFrame) -> pd.DataFrame:
    ds = xr.open_dataset(COAST_NC)
    lon = ds["station_x_coordinate"].values.astype(float)
    lat = ds["station_y_coordinate"].values.astype(float)
    rp_values = {rp: ds[var].values.astype(float) for rp, var in RP_VARS.items()}
    out = []
    for _, st in rows.iterrows():
        dist = np.array([haversine_km(float(st["lon"]), float(st["lat"]), float(x), float(y)) for x, y in zip(lon, lat)])
        idx = int(np.nanargmin(dist))
        row = {
            "station_id": st["station_id"],
            "coast_rp_idx": idx,
            "match_dist_km": float(dist[idx]),
        }
        for rp, values in rp_values.items():
            row[f"coast_rp_rp{rp}_m"] = float(values[idx])
        out.append(row)
    return pd.DataFrame(out)


def select_station_ids(meta: pd.DataFrame, corr_threshold: float = 0.55, n: int = 30) -> list[str]:
    archives = github_archives()
    candidates = meta[
        meta["lon"].between(-9.0, 9.0)
        & meta["lat"].between(47.0, 61.0)
        & meta["gssr_archive"].isin(archives)
        & meta["num_year"].ge(25)
        & meta["corrn"].ge(corr_threshold)
    ].copy()
    candidates["core"] = candidates["station_id"].isin(CORE_SITE_IDS)
    candidates = candidates.sort_values(["core", "num_year", "corrn"], ascending=[False, False, False])
    core = candidates[candidates["core"]].copy()
    fill = candidates[~candidates["core"]].sort_values(["num_year", "corrn"], ascending=False).head(max(0, n - len(core)))
    return pd.concat([core, fill], ignore_index=True).drop_duplicates("station_id").head(n)["station_id"].tolist()


def rank_stats(frame: pd.DataFrame, water_col: str, terrain_col: str) -> dict[str, float | int | str]:
    ok = frame.dropna(subset=[water_col, terrain_col]).copy()
    ok["water_rank"] = ok[water_col].rank(ascending=False, method="min").astype(int)
    ok["terrain_rank"] = ok[terrain_col].rank(ascending=False, method="min").astype(int)
    top_n = max(1, math.ceil(0.2 * len(ok)))
    top_water = set(ok.nsmallest(top_n, "water_rank")["station_id"])
    top_terrain = set(ok.nsmallest(top_n, "terrain_rank")["station_id"])
    overlap = len(top_water & top_terrain)
    return {
        "n_sites": int(len(ok)),
        "top_n": int(top_n),
        "top_overlap": int(overlap),
        "top_mismatch_fraction": float(1 - overlap / top_n),
        "spearman": float(ok[water_col].corr(ok[terrain_col], method="spearman")),
        "kendall": float(ok[water_col].corr(ok[terrain_col], method="kendall")),
        "top_water_sites": ";".join(sorted(top_water)),
        "top_terrain_sites": ";".join(sorted(top_terrain)),
    }


def build_candidate_audit() -> pd.DataFrame:
    meta = load_metadata()
    archives = github_archives()
    base = pd.read_csv(BASE_SCREENING)
    selected_ids = set(base["station_id"])
    in_region = meta[meta["lon"].between(-9.0, 9.0) & meta["lat"].between(47.0, 61.0)].copy()
    in_region["archive_available"] = in_region["gssr_archive"].isin(archives)
    in_region["passes_years_ge25"] = in_region["num_year"].ge(25)
    for threshold in [0.45, 0.55, 0.65]:
        in_region[f"passes_corr_ge{str(threshold).replace('.', '')}"] = in_region["corrn"].ge(threshold)
    in_region["selected_base_30"] = in_region["station_id"].isin(selected_ids)
    in_region = in_region.merge(nearest_coastrp_for_rows(in_region), on="station_id", how="left")
    tile_rows = []
    for _, row in in_region.iterrows():
        try:
            ok, tiles = tile_availability_for_bbox(bbox_for_station(float(row["lon"]), float(row["lat"])))
        except Exception as exc:  # noqa: BLE001
            ok, tiles = False, f"tile check error: {exc}"
        tile_rows.append({"station_id": row["station_id"], "deltadtm_tile_available": ok, "deltadtm_tiles": tiles})
    in_region = in_region.merge(pd.DataFrame(tile_rows), on="station_id", how="left")

    def reason(row: pd.Series) -> str:
        if row["selected_base_30"]:
            return "included in baseline 30-station subset"
        if not row["archive_available"]:
            return "excluded: GSSR ERA5 archive not available in cached GitHub listing"
        if not row["passes_years_ge25"]:
            return "excluded: fewer than 25 metadata years"
        if not row["passes_corr_ge055"]:
            return "excluded: reconstruction correlation below 0.55"
        return "excluded: passed filters but outside top-30 fill after retaining focal core sites"

    in_region["selection_reason"] = in_region.apply(reason, axis=1)
    cols = [
        "station_id",
        "station",
        "tg",
        "lat",
        "lon",
        "num_year",
        "corrn",
        "rmse",
        "gssr_archive",
        "archive_available",
        "passes_years_ge25",
        "passes_corr_ge045",
        "passes_corr_ge055",
        "passes_corr_ge065",
        "selected_base_30",
        "selection_reason",
        "match_dist_km",
        "coast_rp_rp10_m",
        "deltadtm_tile_available",
        "deltadtm_tiles",
    ]
    out = in_region[cols].sort_values(["selected_base_30", "num_year", "corrn"], ascending=[False, False, False])
    out.to_csv(FIG_SOURCE / "Fig5_station_candidate_audit.csv", index=False)
    return out


def build_subset_threshold_sensitivity(base: pd.DataFrame) -> pd.DataFrame:
    meta = load_metadata()
    rows = []
    for threshold in [0.45, 0.55, 0.65]:
        selected = select_station_ids(meta, corr_threshold=threshold, n=30)
        frame = base[base["station_id"].isin(selected)].copy()
        stats = rank_stats(frame, "coast_rp_rp10_m", "connected_2m_lowland_pct")
        stats.update(
            {
                "diagnostic": "corr-threshold sensitivity",
                "corr_threshold": threshold,
                "target_n": 30,
                "selected_overlap_with_baseline": int(len(set(selected) & set(base["station_id"]))),
                "selected_ids": ";".join(selected),
            }
        )
        rows.append(stats)
    for n in [20, 25, 30]:
        selected = select_station_ids(meta, corr_threshold=0.55, n=n)
        frame = base[base["station_id"].isin(selected)].copy()
        stats = rank_stats(frame, "coast_rp_rp10_m", "connected_2m_lowland_pct")
        stats.update(
            {
                "diagnostic": "subset-size sensitivity at corr>=0.55",
                "corr_threshold": 0.55,
                "target_n": n,
                "selected_overlap_with_baseline": int(len(set(selected) & set(base["station_id"]))),
                "selected_ids": ";".join(selected),
            }
        )
        rows.append(stats)
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig5_subset_selection_threshold_sensitivity.csv", index=False)
    return out


def connected_mask_with_seed_mode(
    elev: np.ndarray,
    valid: np.ndarray,
    eta: float,
    seed_mode: str,
    connectivity: int = 8,
) -> np.ndarray:
    if seed_mode == "boundary_water_nodata":
        return flood_connectivity_layers(elev, valid, eta, connectivity=connectivity)["connected"]
    if seed_mode == "boundary_water_plus_edge_lowland":
        low = valid & np.isfinite(elev) & (elev <= eta)
        ocean = ~valid
        seed = boundary_ocean_seed(valid)
        edge_low = np.zeros(low.shape, dtype=bool)
        edge_low[0, :] = low[0, :]
        edge_low[-1, :] |= low[-1, :]
        edge_low[:, 0] |= low[:, 0]
        edge_low[:, -1] |= low[:, -1]
        ocean_reachable, _ = flood_fill(ocean, seed, connectivity=connectivity)
        passable = low | ocean_reachable
        reachable, _ = flood_fill(passable, seed | edge_low, connectivity=connectivity)
        return reachable & low
    raise ValueError(f"Unknown seed mode: {seed_mode}")


def terrain_percentages(
    row: pd.Series,
    buffer_deg: float = 0.04,
    lowland_max_m: float = 15.0,
    eta_values: list[float] | None = None,
    seed_mode: str = "boundary_water_nodata",
) -> dict[str, object]:
    eta_values = ETA_LEVELS if eta_values is None else eta_values
    bbox = bbox_for_station(float(row["lon"]), float(row["lat"]), buffer_deg=buffer_deg)
    ensure_tiles_for_bbox(bbox)
    lon2d, lat2d, elev, source, _, tiles = load_dem(bbox, allow_synthetic=False)
    valid = valid_mask(elev)
    coast = valid & (elev <= lowland_max_m)
    denom = int(coast.sum())
    out: dict[str, object] = {
        "station_id": row["station_id"],
        "buffer_deg": buffer_deg,
        "lowland_max_m": lowland_max_m,
        "seed_mode": seed_mode,
        "terrain_source": source,
        "terrain_tiles": ";".join(tiles),
        "coastal_lowland_cells": denom,
    }
    for eta in eta_values:
        low = valid & np.isfinite(elev) & (elev <= eta)
        connected = connected_mask_with_seed_mode(elev, valid, eta, seed_mode=seed_mode, connectivity=8)
        out[f"connected_{eta:g}m_lowland_pct"] = float(100 * (connected & coast).sum() / denom) if denom else np.nan
        out[f"bathtub_{eta:g}m_lowland_pct"] = float(100 * (low & coast).sum() / denom) if denom else np.nan
    return out


def build_candidate_pool_threshold_sensitivity(audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pool = audit[
        audit["archive_available"].eq(True)
        & audit["passes_years_ge25"].eq(True)
        & audit["passes_corr_ge045"].eq(True)
        & audit["deltadtm_tile_available"].eq(True)
    ].copy()
    required_ids = set(pool["station_id"])
    if CANDIDATE_POOL_SCREENING.exists():
        cached = pd.read_csv(CANDIDATE_POOL_SCREENING)
        if required_ids.issubset(set(cached["station_id"])) and {"connected_2m_lowland_pct", "coast_rp_rp10_m"}.issubset(cached.columns):
            screening = cached[cached["station_id"].isin(required_ids)].copy()
        else:
            screening = pd.DataFrame()
    else:
        screening = pd.DataFrame()

    if screening.empty:
        rows = []
        for _, row in pool.iterrows():
            base = row[
                [
                    "station_id",
                    "station",
                    "tg",
                    "lat",
                    "lon",
                    "num_year",
                    "corrn",
                    "match_dist_km",
                    "coast_rp_rp10_m",
                    "selected_base_30",
                ]
            ].to_dict()
            try:
                base.update(terrain_percentages(row, buffer_deg=0.04, lowland_max_m=15.0, eta_values=[2.0]))
                base["candidate_pool_status"] = "ok"
            except Exception as exc:  # noqa: BLE001
                base["candidate_pool_status"] = "terrain error"
                base["candidate_pool_error"] = str(exc)
            rows.append(base)
        screening = pd.DataFrame(rows)
        screening.to_csv(CANDIDATE_POOL_SCREENING, index=False)

    rows = []
    for threshold in [0.45, 0.55, 0.65]:
        frame = screening[screening["corrn"].ge(threshold)].dropna(subset=["coast_rp_rp10_m", "connected_2m_lowland_pct"]).copy()
        stats = rank_stats(frame, "coast_rp_rp10_m", "connected_2m_lowland_pct")
        stats.update(
            {
                "diagnostic": "candidate-pool threshold sensitivity",
                "corr_threshold": threshold,
                "target_n": "all eligible",
                "selected_overlap_with_baseline": int(frame["selected_base_30"].sum()),
                "selected_ids": ";".join(frame["station_id"].tolist()),
            }
        )
        rows.append(stats)
    summary = pd.DataFrame(rows)
    summary.to_csv(FIG_SOURCE / "Fig5_candidate_pool_threshold_sensitivity.csv", index=False)
    return screening, summary


def build_rank_robustness(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for _, row in base.iterrows():
        rows.append(terrain_percentages(row, buffer_deg=0.04, lowland_max_m=15.0, eta_values=ETA_LEVELS))
    terrain = pd.DataFrame(rows)
    coast = nearest_coastrp_for_rows(base)
    robust = base.drop(
        columns=[
            c
            for c in base.columns
            if c.startswith("connected_") or c.startswith("bathtub_") or c.startswith("coast_rp_rp")
        ],
        errors="ignore",
    ).merge(coast, on="station_id", how="left").merge(
        terrain[
            [
                "station_id",
                "connected_1m_lowland_pct",
                "connected_2m_lowland_pct",
                "connected_3m_lowland_pct",
                "bathtub_1m_lowland_pct",
                "bathtub_2m_lowland_pct",
                "bathtub_3m_lowland_pct",
            ]
        ],
        on="station_id",
        how="left",
    )
    robust.to_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening_robust.csv", index=False)

    rows = []
    for rp in [10, 50, 100]:
        for eta in ETA_LEVELS:
            water_col = f"coast_rp_rp{rp}_m"
            terrain_col = f"connected_{eta:g}m_lowland_pct"
            stats = rank_stats(robust, water_col, terrain_col)
            stats.update({"water_metric": f"COAST-RP RP{rp}", "terrain_metric": f"+{eta:g} m connected", "rp_year": rp, "eta_m": eta})
            rows.append(stats)
    summary = pd.DataFrame(rows)
    summary.to_csv(FIG_SOURCE / "Fig5_rank_discordance_robustness.csv", index=False)
    return robust, summary


def build_terrain_screen_sensitivity(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    focal_ids = ["sheerness-p015-uk", "hoekvanholla-hvh-nl", "newlyn-p001-uk", "brest", "aberdeen-p038-uk"]
    focal = base[base["station_id"].isin(focal_ids)].copy()
    rows = []
    for _, row in focal.iterrows():
        for buffer_deg in [0.03, 0.04, 0.06]:
            out = terrain_percentages(row, buffer_deg=buffer_deg, lowland_max_m=15.0, eta_values=[2.0])
            out["sensitivity_type"] = "window_size"
            out["setting"] = f"buffer={buffer_deg:g} deg"
            rows.append(out)
        for lowland_max in [10.0, 15.0, 20.0]:
            out = terrain_percentages(row, buffer_deg=0.04, lowland_max_m=lowland_max, eta_values=[2.0])
            out["sensitivity_type"] = "lowland_denominator"
            out["setting"] = f"lowland<={lowland_max:g} m"
            rows.append(out)
        for seed_mode in ["boundary_water_nodata", "boundary_water_plus_edge_lowland"]:
            out = terrain_percentages(row, buffer_deg=0.04, lowland_max_m=15.0, eta_values=[2.0], seed_mode=seed_mode)
            out["sensitivity_type"] = "boundary_seed"
            out["setting"] = seed_mode
            rows.append(out)
    detail = pd.DataFrame(rows)
    detail.to_csv(FIG_SOURCE / "Fig4_terrain_window_denominator_seed_sensitivity.csv", index=False)
    summary = (
        detail.groupby(["station_id", "sensitivity_type"], as_index=False)
        .agg(
            n_settings=("setting", "nunique"),
            connected_2m_min_pct=("connected_2m_lowland_pct", "min"),
            connected_2m_max_pct=("connected_2m_lowland_pct", "max"),
            bathtub_2m_min_pct=("bathtub_2m_lowland_pct", "min"),
            bathtub_2m_max_pct=("bathtub_2m_lowland_pct", "max"),
        )
        .sort_values(["station_id", "sensitivity_type"])
    )
    summary.to_csv(FIG_SOURCE / "Fig4_terrain_screen_sensitivity_summary.csv", index=False)
    return detail, summary


def main() -> int:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE_SCREENING)
    audit = build_candidate_audit()
    threshold = build_subset_threshold_sensitivity(base)
    pool, pool_threshold = build_candidate_pool_threshold_sensitivity(audit)
    robust, rank = build_rank_robustness(base)
    terrain_detail, terrain_summary = build_terrain_screen_sensitivity(base)
    print("Candidate audit")
    print(audit["selection_reason"].value_counts().to_string())
    print("\nSubset threshold sensitivity")
    print(threshold[["diagnostic", "corr_threshold", "target_n", "n_sites", "spearman", "kendall", "top_overlap", "top_n", "top_mismatch_fraction"]].to_string(index=False))
    print("\nCandidate-pool threshold sensitivity")
    print(pool_threshold[["diagnostic", "corr_threshold", "target_n", "n_sites", "spearman", "kendall", "top_overlap", "top_n", "top_mismatch_fraction"]].to_string(index=False))
    print("\nRank-discordance robustness")
    print(rank[["water_metric", "terrain_metric", "spearman", "kendall", "top_overlap", "top_n", "top_mismatch_fraction"]].to_string(index=False))
    print("\nTerrain screen sensitivity summary")
    print(terrain_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

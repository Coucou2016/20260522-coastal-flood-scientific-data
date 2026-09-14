#!/usr/bin/env python3
"""Download and compare local high-resolution DTM windows against DeltaDTM.

This is an elevation-product and datum sensitivity analysis, not a validation
against a common flood surface. The script fetches official local terrain rasters for a
small set of representative stations, downsamples them to a 10 m analysis grid
through the provider WCS, and reruns the same static connectivity screen using
the already audited DeltaDTM official mask classes as the water-seed source.
Finite official-mask class-0 terrain forms the fixed-window reference-land
support; water, clipped and outside-support cells are excluded.

The comparison therefore tests the sensitivity of the connected-terrain metric
to the elevation product while keeping the seed rule constant:

* Environment Agency LiDAR Composite DTM 2 m WCS for England, scaled to 10 m.
* PDOK/Rijkswaterstaat AHN DTM 0.5 m WCS for the Netherlands, scaled to 10 m.

Vertical datums are not harmonised here. The 2 m threshold is applied in each
local product's native vertical datum and is interpreted as a screening
cross-check rather than an absolute flood-level equivalence test.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.warp import reproject
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from add_advanced_terrain_rank_diagnostics import cell_area_km2, read_dem_window_fast, sum_area  # noqa: E402
from add_mask_aware_terrain_diagnostics import (  # noqa: E402
    MASK_OUTSIDE_SUPPORT,
    mask_aware_layers,
    resolve_marine_seed,
)
from inundation_sensitivity import valid_mask  # noqa: E402
from publication_style import apply_publication_style  # noqa: E402

FIG_SOURCE = ROOT / "data" / "figure_source"
RAW_LOCAL = ROOT / "data" / "raw" / "local_dtm"
FIG_LOCAL = ROOT / "figures" / "supplementary"
FIG_MAIN = ROOT / "figures" / "main"

STATIONS = [
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "lowestoft-p024-uk",
    "immingham-p026-uk",
    "denhelder-hel-nl",
    "delfzijl-del-nl",
    "hoekvanholla-hvh-nl",
]

DISPLAY_NAMES = {
    "sheerness-p015-uk": "Sheerness",
    "newlyn-p001-uk": "Newlyn",
    "lowestoft-p024-uk": "Lowestoft",
    "immingham-p026-uk": "Immingham",
    "denhelder-hel-nl": "Den Helder",
    "delfzijl-del-nl": "Delfzijl",
    "hoekvanholla-hvh-nl": "Hoek van Holland",
}


@dataclass(frozen=True)
class WcsConfig:
    source_name: str
    service_url: str
    coverage_id: str
    crs: str
    axis_x: str
    axis_y: str
    scale_factor: str
    native_resolution_m: float
    analysis_resolution_m: float
    vertical_datum: str


EA_LIDAR_2M = WcsConfig(
    source_name="Environment Agency LiDAR Composite DTM 2 m WCS, scaleFactor 0.2",
    service_url="https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-2m/wcs",
    coverage_id="09ea3b37-df3a-4e8b-ac69-fb0842227b04__Lidar_Composite_Elevation_DTM_2m",
    crs="EPSG:27700",
    axis_x="E",
    axis_y="N",
    scale_factor="0.2",
    native_resolution_m=2.0,
    analysis_resolution_m=10.0,
    vertical_datum="Ordnance Datum Newlyn / EA product native datum",
)

AHN_DTM_05M = WcsConfig(
    source_name="PDOK/Rijkswaterstaat AHN DTM 0.5 m WCS, scaleFactor 0.05",
    service_url="https://service.pdok.nl/rws/ahn/wcs/v1_0",
    coverage_id="dtm_05m",
    crs="EPSG:28992",
    axis_x="x",
    axis_y="y",
    scale_factor="0.05",
    native_resolution_m=0.5,
    analysis_resolution_m=10.0,
    vertical_datum="Normaal Amsterdams Peil / AHN product native datum",
)


def station_config(station_id: str) -> WcsConfig:
    if station_id.endswith("-uk"):
        return EA_LIDAR_2M
    if station_id.endswith("-nl"):
        return AHN_DTM_05M
    raise ValueError(f"No local DTM WCS configured for {station_id}")


def transform_bbox(
    bbox: tuple[float, float, float, float],
    target_crs: str,
) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    points = [
        transformer.transform(west, south),
        transformer.transform(west, north),
        transformer.transform(east, south),
        transformer.transform(east, north),
    ]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_wcs(station_id: str, bbox: tuple[float, float, float, float], cfg: WcsConfig) -> Path:
    import requests

    RAW_LOCAL.mkdir(parents=True, exist_ok=True)
    target = RAW_LOCAL / f"{station_id}_local_dtm_10m.tif"
    if target.exists() and target.stat().st_size > 1024:
        return target

    xmin, ymin, xmax, ymax = transform_bbox(bbox, cfg.crs)
    params = {
        "service": "WCS",
        "version": "2.0.1",
        "request": "GetCoverage",
        "coverageId": cfg.coverage_id,
        "format": "image/tiff",
        "subset": [f"{cfg.axis_x}({xmin},{xmax})", f"{cfg.axis_y}({ymin},{ymax})"],
        "scaleFactor": cfg.scale_factor,
    }
    last_error: Exception | None = None
    for attempt in range(1, 5):
        try:
            response = requests.get(cfg.service_url, params=params, timeout=300)
            content = response.content
            break
        except requests.RequestException as exc:
            last_error = exc
            sleep(3 * attempt)
    else:
        raise RuntimeError(f"WCS download failed for {station_id} after retries: {last_error}")

    if response.status_code != 200 or content[:4] not in (b"II*\x00", b"MM\x00*"):
        snippet = response.text[:500] if response.text else str(content[:120])
        raise RuntimeError(
            f"WCS download failed for {station_id}: {response.status_code} "
            f"{response.headers.get('content-type')} {snippet}"
        )
    target.write_bytes(content)
    return target


def reproject_mask_to_local(
    mask_src: np.ndarray,
    mask_transform: rasterio.Affine,
    dst_shape: tuple[int, int],
    dst_transform: rasterio.Affine,
    dst_crs: str,
) -> np.ndarray:
    dst = np.full(dst_shape, MASK_OUTSIDE_SUPPORT, dtype=np.uint8)
    reproject(
        mask_src,
        dst,
        src_transform=mask_transform,
        src_crs="EPSG:4326",
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        src_nodata=int(MASK_OUTSIDE_SUPPORT),
        dst_nodata=int(MASK_OUTSIDE_SUPPORT),
        resampling=Resampling.nearest,
    )
    return dst


def reproject_binary_to_local(
    layer_src: np.ndarray,
    src_transform: rasterio.Affine,
    dst_shape: tuple[int, int],
    dst_transform: rasterio.Affine,
    dst_crs: str,
) -> np.ndarray:
    src = layer_src.astype(np.uint8)
    dst = np.zeros(dst_shape, dtype=np.uint8)
    reproject(
        src,
        dst,
        src_transform=src_transform,
        src_crs="EPSG:4326",
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        src_nodata=0,
        dst_nodata=0,
        resampling=Resampling.nearest,
    )
    return dst.astype(bool)


def local_valid_mask(elev: np.ndarray, nodata: float | int | None) -> np.ndarray:
    valid = np.isfinite(elev)
    if nodata is not None and np.isfinite(nodata):
        valid &= elev != nodata
    valid &= elev > -100
    valid &= elev < 500
    return valid


def area_grid_km2(shape: tuple[int, int], transform: rasterio.Affine) -> np.ndarray:
    area = abs(float(transform.a) * float(transform.e)) / 1_000_000.0
    return np.full(shape, area, dtype=float)


def classify(
    elev: np.ndarray,
    valid: np.ndarray,
    mask: np.ndarray,
    area: np.ndarray,
    level: float = 2.0,
    tidal_water: np.ndarray | None = None,
) -> dict[str, object]:
    layers = mask_aware_layers(elev, valid, mask, level, tidal_water=tidal_water)
    ocean = layers["ocean"]
    river = layers["river"]
    lake = layers["lake"]
    clipped = layers["clipped"]
    outside_support = layers["outside_support"]
    tidal_water = layers["tidal_water"]
    land = layers["land"]
    reference_land = land
    low = layers["low"]
    connected = ndi.binary_propagation(
        tidal_water,
        structure=ndi.generate_binary_structure(2, 1),
        mask=low | tidal_water,
    ) & low
    conn_area = sum_area(area, connected)
    below_area = sum_area(area, low)
    reference_land_area = sum_area(area, reference_land)
    return {
        "reference_land": reference_land,
        "low": low,
        "connected": connected,
        "tidal_water": tidal_water,
        "reference_land_area_km2": reference_land_area,
        "connected_area_km2": conn_area,
        "all_below_area_km2": below_area,
        "unconnected_area_km2": max(below_area - conn_area, 0.0),
        "connected_reference_land_pct": (
            100.0 * conn_area / reference_land_area if reference_land_area else np.nan
        ),
        "below_reference_land_pct": (
            100.0 * below_area / reference_land_area if reference_land_area else np.nan
        ),
        "conditional_connectivity_pct": (
            100.0 * conn_area / below_area if below_area else np.nan
        ),
        "valid_cells": int(valid.sum()),
        "ocean_cells_reprojected": int(ocean.sum()),
        "river_cells_reprojected": int(river.sum()),
        "lake_cells_reprojected": int(lake.sum()),
        "clipped_cells_reprojected": int(clipped.sum()),
        "outside_support_cells_reprojected": int(outside_support.sum()),
    }


def process_station(row: pd.Series) -> dict[str, object]:
    station_id = str(row["station_id"])
    cfg = station_config(station_id)
    bbox = (
        float(row["bbox_west"]),
        float(row["bbox_south"]),
        float(row["bbox_east"]),
        float(row["bbox_north"]),
    )
    local_path = download_wcs(station_id, bbox, cfg)
    with rasterio.open(local_path) as src:
        local = src.read(1).astype(float)
        local_transform = src.transform
        local_crs = src.crs.to_string()
        nodata = src.nodata
        local_shape = local.shape
    valid_local = local_valid_mask(local, nodata)
    area_local = area_grid_km2(local_shape, local_transform)

    lon2d, lat2d, delta_elev, _dem_source, dem_meta, _dem_tiles = read_dem_window_fast(bbox)
    delta_valid = valid_mask(delta_elev)
    delta_mask, delta_tidal, seed_audit = resolve_marine_seed(
        float(row["lon"]),
        float(row["lat"]),
        bbox,
        delta_elev.shape,
        dem_meta["transform"],
        dem_meta["crs"],
    )
    local_mask = reproject_mask_to_local(
        delta_mask,
        dem_meta["transform"],
        local_shape,
        local_transform,
        local_crs,
    )
    local_tidal = reproject_binary_to_local(
        delta_tidal,
        dem_meta["transform"],
        local_shape,
        local_transform,
        local_crs,
    )
    local_result = classify(
        local,
        valid_local,
        local_mask,
        area_local,
        level=2.0,
        tidal_water=local_tidal,
    )

    delta_layers = mask_aware_layers(
        delta_elev,
        delta_valid,
        delta_mask,
        2.0,
        tidal_water=delta_tidal,
    )
    delta_connected = ndi.binary_propagation(
        delta_tidal,
        structure=ndi.generate_binary_structure(2, 1),
        mask=delta_layers["low"] | delta_tidal,
    ) & delta_layers["low"]
    delta_result = classify(
        delta_elev,
        delta_valid,
        delta_mask,
        cell_area_km2(lon2d, lat2d),
        level=2.0,
        tidal_water=delta_tidal,
    )
    delta_transform = dem_meta["transform"]
    delta_connected_on_local = reproject_binary_to_local(
        delta_connected,
        delta_transform,
        local_shape,
        local_transform,
        local_crs,
    )

    local_connected = local_result["connected"]
    intersection = local_connected & delta_connected_on_local
    union = local_connected | delta_connected_on_local
    iou = float(intersection.sum() / union.sum()) if union.sum() else np.nan

    delta_fraction = float(delta_result["connected_reference_land_pct"])
    delta_below_fraction = float(delta_result["below_reference_land_pct"])
    delta_conditional = float(delta_result["conditional_connectivity_pct"])
    delta_area = float(delta_result["connected_area_km2"])
    local_fraction = float(local_result["connected_reference_land_pct"])
    local_below_fraction = float(local_result["below_reference_land_pct"])
    local_conditional = float(local_result["conditional_connectivity_pct"])
    local_area = float(local_result["connected_area_km2"])

    return {
        "station_id": station_id,
        "station": row["station"],
        "country_or_provider": "England Environment Agency" if cfg is EA_LIDAR_2M else "Netherlands PDOK/Rijkswaterstaat",
        "local_dtm_source": cfg.source_name,
        "local_dtm_service_url": cfg.service_url,
        "local_dtm_coverage_id": cfg.coverage_id,
        "local_dtm_crs": cfg.crs,
        "local_dtm_vertical_datum_note": cfg.vertical_datum,
        "native_resolution_m": cfg.native_resolution_m,
        "analysis_resolution_m": cfg.analysis_resolution_m,
        "local_dtm_path": str(local_path.relative_to(ROOT)),
        "local_dtm_sha256": sha256(local_path),
        "continuous_elevation_resampling": "provider WCS scaleFactor to nominal 10 m; interpolation kernel controlled by provider service",
        "categorical_mask_resampling": "nearest neighbour from DeltaDTM grid to local analysis grid",
        "connected_mask_resampling_for_iou": "nearest neighbour from DeltaDTM grid to local analysis grid",
        "land_connectivity_neighbour_rule": 4,
        "iou_target_grid": "local DTM WCS grid",
        "local_grid_shape": f"{local_shape[0]}x{local_shape[1]}",
        "local_grid_transform": str(local_transform),
        "delta_connected_2m_reference_land_pct": delta_fraction,
        "local_connected_2m_reference_land_pct": local_fraction,
        "fraction_difference_local_minus_delta_pct_points": local_fraction - delta_fraction,
        "delta_below_2m_reference_land_pct": delta_below_fraction,
        "local_below_2m_reference_land_pct": local_below_fraction,
        "delta_conditional_connectivity_2m_pct": delta_conditional,
        "local_conditional_connectivity_2m_pct": local_conditional,
        "delta_connected_2m_area_km2": delta_area,
        "local_connected_2m_area_km2": local_area,
        "area_difference_local_minus_delta_km2": local_area - delta_area,
        "connected_pixel_iou_after_reprojection": iou,
        "local_reference_land_area_km2": local_result["reference_land_area_km2"],
        "local_all_below_2m_area_km2": local_result["all_below_area_km2"],
        "local_unconnected_2m_area_km2": local_result["unconnected_area_km2"],
        "local_valid_cells": local_result["valid_cells"],
        "local_ocean_cells_reprojected": local_result["ocean_cells_reprojected"],
        "local_river_cells_reprojected": local_result["river_cells_reprojected"],
        "local_lake_cells_reprojected": local_result["lake_cells_reprojected"],
        "local_clipped_cells_reprojected": local_result["clipped_cells_reprojected"],
        "local_outside_support_cells_reprojected": local_result["outside_support_cells_reprojected"],
        "marine_seed_status": seed_audit["marine_seed_status"],
        "marine_context_width_km": seed_audit["marine_context_width_km"],
        "crosscheck_scope": "elevation-product and native-datum sensitivity; vertical datums not harmonized; official DeltaDTM mask seed and fixed-window reference-land mask held constant",
    }


def write_crosscheck_figure(rows: list[dict[str, object]]) -> None:
    import matplotlib.pyplot as plt

    apply_publication_style()
    FIG_LOCAL.mkdir(parents=True, exist_ok=True)
    FIG_MAIN.mkdir(parents=True, exist_ok=True)
    labels = [DISPLAY_NAMES.get(str(r["station_id"]), str(r["station"])) for r in rows]
    y = np.arange(len(rows))[::-1]
    delta = np.asarray([r["delta_connected_2m_reference_land_pct"] for r in rows], dtype=float)
    local = np.asarray([r["local_connected_2m_reference_land_pct"] for r in rows], dtype=float)

    iou = np.asarray([r["connected_pixel_iou_after_reprojection"] for r in rows], dtype=float)

    fig, (ax, ax_iou) = plt.subplots(
        1,
        2,
        figsize=(11.2, 4.9),
        gridspec_kw={"width_ratios": [1.55, 0.85], "wspace": 0.28},
    )
    for yi, d, l, r in zip(y, delta, local, rows):
        ax.plot([d, l], [yi, yi], color="#64748B", lw=2.0, alpha=0.55, zorder=1)
    ax.scatter(delta, y, label="DeltaDTM + official mask", color="#2563A8", edgecolor="white", linewidth=0.7, s=55, zorder=3)
    ax.scatter(local, y, label="Local DTM + same mask seed", color="#C47A1C", marker="s", edgecolor="white", linewidth=0.7, s=50, zorder=3)
    ax.set_xlabel("Connected below-threshold share of reference land at 2 m (%)")
    ax.set_yticks(y, labels)
    ax.set_xlim(-2, 104)
    ax.grid(axis="x", color="#D7DEE7", linewidth=0.6)
    handles, labels_legend = ax.get_legend_handles_labels()
    fig.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=2)
    for yi, d, l, r in zip(y, delta, local, rows):
        ax.text(d, yi + 0.18, f"{d:.1f}", ha="center", va="bottom", fontsize=7.2, color="#1F4E79")
        ax.text(l, yi - 0.18, f"{l:.1f}", ha="center", va="top", fontsize=7.2, color="#8A4F08")
    ax.set_title("a. Connected fraction in each native height reference", loc="left", fontweight="bold")

    ax_iou.scatter(iou, y, c="#4B5563", s=52, edgecolor="white", linewidth=0.7, zorder=3)
    for xi, yi in zip(iou, y):
        ax_iou.text(xi + 0.025, yi, f"{xi:.2f}", va="center", fontsize=7.2, color="#334155")
    ax_iou.set_xlim(-0.03, 1.06)
    ax_iou.set_xlabel("Connected-cell intersection over union")
    ax_iou.set_yticks(y, labels)
    ax_iou.grid(axis="x", color="#D7DEE7", linewidth=0.6)
    ax_iou.set_title("b. Spatial agreement after reprojection", loc="left", fontweight="bold")

    fig.text(
        0.5,
        0.025,
        "Native vertical datums were not harmonized; differences combine elevation-product and datum effects.",
        ha="center",
        va="bottom",
        fontsize=8.2,
        color="#475569",
    )
    fig.subplots_adjust(left=0.12, right=0.985, top=0.84, bottom=0.19)
    for folder in [FIG_LOCAL, FIG_MAIN]:
        fig.savefig(folder / "Fig4_elevation_product_datum_sensitivity.png", dpi=450, bbox_inches="tight")
        fig.savefig(folder / "Fig4_elevation_product_datum_sensitivity.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    metrics = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    selected = metrics[metrics["station_id"].isin(STATIONS)].copy()
    missing = set(STATIONS) - set(selected["station_id"])
    if missing:
        raise RuntimeError(f"Missing validation stations in mask-aware metrics table: {sorted(missing)}")
    rows = []
    for station_id in STATIONS:
        row = selected[selected["station_id"].eq(station_id)].iloc[0]
        print(f"Local DTM product/datum cross-check: {station_id}", flush=True)
        rows.append(process_station(row))
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv", index=False)
    write_crosscheck_figure(rows)
    print(out[
        [
            "station_id",
            "delta_connected_2m_reference_land_pct",
            "local_connected_2m_reference_land_pct",
            "fraction_difference_local_minus_delta_pct_points",
            "delta_connected_2m_area_km2",
            "local_connected_2m_area_km2",
            "connected_pixel_iou_after_reprojection",
        ]
    ].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

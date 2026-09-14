#!/usr/bin/env python3
"""
Static bathtub inundation sensitivity (+0.5 / +1.0 / +2.0 m relative SLR).

Uses DeltaDTM COG tiles under data/raw/deltadtm/tiles/ (real EGM2008 elevations).
Skips stations without local tiles unless --allow-synthetic is set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from matplotlib.gridspec import GridSpec
from shapely.geometry import box

from combo1_utils import CONFIG, FIGURES, PROCESSED, RAW, ensure_dirs, load_config

SLR_LEVELS = [0.5, 1.0, 2.0]
TILE_INDEX = RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg"
TILES_DIR = RAW / "deltadtm" / "tiles"
NODATA = -9999.0
COASTAL_ELEV_MAX_M = 15.0

EU_STATION_IDS = {
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest-france",
}


def station_bbox(station: dict, buffer_deg: float = 0.04) -> tuple[float, float, float, float]:
    return (
        station["lon"] - buffer_deg,
        station["lat"] - buffer_deg,
        station["lon"] + buffer_deg,
        station["lat"] + buffer_deg,
    )


def tiles_for_bbox(bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(TILE_INDEX)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    region = gpd.GeoDataFrame(geometry=[box(*bbox)], crs=4326)
    return gdf[gdf.intersects(region.geometry.iloc[0])]


MIN_TILE_BYTES = 100_000


def _tile_tif_paths(tile_field: str) -> list[Path]:
    name = Path(str(tile_field).strip())
    if not name.name:
        return []
    direct = TILES_DIR / name.name
    if direct.exists() and direct.stat().st_size > MIN_TILE_BYTES:
        return [direct]
    stem = name.stem
    return sorted(
        p for p in TILES_DIR.rglob(f"*{stem}*.tif") if p.stat().st_size > MIN_TILE_BYTES
    )


def synthetic_dem(bbox: tuple[float, float, float, float], res: int = 80) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    west, south, east, north = bbox
    lon = np.linspace(west, east, res)
    lat = np.linspace(south, north, res)
    lon2d, lat2d = np.meshgrid(lon, lat)
    dist_offshore = (lon2d - west) / max(east - west, 1e-6)
    elev = 2.0 - 7.0 * dist_offshore + 0.3 * (lat2d - lat2d.mean())
    return lon2d, lat2d, elev


def _read_dem_window(path: Path, bbox: tuple[float, float, float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(path) as src:
        window = from_bounds(*bbox, transform=src.transform)
        elev = src.read(1, window=window, masked=True).astype(float)
        elev = np.ma.filled(elev, np.nan)
        h, w = elev.shape
        west, south, east, north = bbox
        lon = np.linspace(west, east, w)
        lat = np.linspace(south, north, h)
        lon2d, lat2d = np.meshgrid(lon, lat)
        meta = {
            "crs": str(src.crs),
            "resolution": src.res,
            "nodata": src.nodata,
            "tile_file": path.name,
        }
        return lon2d, lat2d, elev, meta


def load_dem(
    bbox: tuple[float, float, float, float],
    allow_synthetic: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, dict, list[str]]:
    tiles = tiles_for_bbox(bbox)
    paths: list[Path] = []
    for _, row in tiles.iterrows():
        paths.extend(_tile_tif_paths(str(row.get("tile", ""))))
    paths = list(dict.fromkeys(paths))

    if paths:
        if len(paths) == 1:
            lon2d, lat2d, elev, meta = _read_dem_window(paths[0], bbox)
            return lon2d, lat2d, elev, f"DeltaDTM:{paths[0].name}", meta, [p.name for p in paths]

        try:
            import rasterio
            from rasterio.merge import merge
            from rasterio.windows import from_bounds

            datasets = [rasterio.open(p) for p in paths]
            try:
                west, south, east, north = bbox
                mosaic, out_transform = merge(
                    datasets,
                    bounds=(west, south, east, north),
                    res=1 / 3600,
                )
                elev = mosaic[0].astype(float)
                elev[elev <= -9000] = np.nan
                h, w = elev.shape
                lon = np.linspace(west, east, w)
                lat = np.linspace(south, north, h)
                lon2d, lat2d = np.meshgrid(lon, lat)
                meta = {
                    "crs": str(datasets[0].crs),
                    "resolution": datasets[0].res,
                    "nodata": datasets[0].nodata,
                    "tile_file": "+".join(p.name for p in paths),
                }
                return lon2d, lat2d, elev, f"DeltaDTM:mosaic({len(paths)})", meta, [p.name for p in paths]
            finally:
                for ds in datasets:
                    ds.close()
        except Exception as exc:  # noqa: BLE001
            print(f"mosaic failed ({exc}); falling back to largest single tile")
            best = max(paths, key=lambda p: p.stat().st_size)
            lon2d, lat2d, elev, meta = _read_dem_window(best, bbox)
            return lon2d, lat2d, elev, f"DeltaDTM:{best.name}", meta, [best.name]

    if allow_synthetic:
        lon2d, lat2d, elev = synthetic_dem(bbox)
        return lon2d, lat2d, elev, "synthetic_coastal_slope", {}, []

    raise FileNotFoundError(
        f"No DeltaDTM tiles on disk for bbox {bbox}. "
        f"Run: python scripts/download_deltadtm_tiles.py --batch-eu --extract"
    )


def valid_mask(elev: np.ndarray) -> np.ndarray:
    return np.isfinite(elev) & (elev > -9000) & (np.abs(elev - NODATA) > 1e-3) & (elev < 50)


def coastal_mask(elev: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if not valid.any():
        return valid
    return valid & (elev <= COASTAL_ELEV_MAX_M)


def flooded_fraction(elev: np.ndarray, slr: float, mask: np.ndarray) -> float:
    if not mask.any():
        return 0.0
    inund = np.maximum(0.0, slr - elev)
    return float((inund[mask] > 0).sum() / mask.sum())


def dem_stats(elev: np.ndarray, valid: np.ndarray) -> dict:
    v = elev[valid]
    if v.size == 0:
        return {}
    return {
        "n_valid_cells": int(valid.sum()),
        "n_total_cells": int(elev.size),
        "valid_fraction": float(valid.sum() / elev.size),
        "elev_min_m": float(v.min()),
        "elev_max_m": float(v.max()),
        "elev_mean_m": float(v.mean()),
        "elev_median_m": float(np.median(v)),
        "elev_below_0m_fraction": float((v < 0).sum() / v.size),
        "elev_below_2m_fraction": float((v < 2).sum() / v.size),
    }


def _hillshade_rgb(elev: np.ndarray, valid: np.ndarray) -> np.ndarray:
    dem = np.where(valid, elev, np.nanmean(elev[valid]) if valid.any() else 0.0)
    dem = np.nan_to_num(dem, nan=0.0)
    ls = LightSource(azdeg=315, altdeg=42)
    shaded = ls.hillshade(dem, vert_exag=2.5)
    rgb = ls.shade(dem, cmap=plt.cm.terrain, blend_mode="overlay", vert_exag=2.5)
    rgb[~valid] = (0.92, 0.92, 0.92, 1.0)
    return rgb


def _plot_dem_panel(ax, lon2d, lat2d, elev, valid, extent, station: dict, source: str) -> None:
    rgb = _hillshade_rgb(elev, valid)
    ax.imshow(rgb, origin="lower", extent=extent, aspect="equal", interpolation="bilinear")
    dem_plot = np.where(valid, elev, np.nan)
    if np.isfinite(dem_plot).any():
        ax.contour(
            lon2d,
            lat2d,
            dem_plot,
            levels=[0, 1, 2, 5],
            colors=["#1a5276", "#2874a6", "#5499c7", "#7d6608"],
            linewidths=0.45,
            alpha=0.85,
        )
    ax.plot(station["lon"], station["lat"], marker="*", color="#c0392b", markersize=14, markeredgecolor="white", markeredgewidth=0.8)
    ax.set_xlabel("经度 °E")
    ax.set_ylabel("纬度 °N")
    label = source.replace("DeltaDTM:", "")
    ax.set_title(f"DeltaDTM 地形\n{label}", fontsize=9, fontweight="bold")


def _plot_inundation_panel(ax, elev, valid, slr, extent, station: dict, frac_all: float, frac_coast: float) -> None:
    depth = np.where(valid, np.maximum(0.0, slr - elev), np.nan)
    land = np.where(valid & (depth <= 0), elev, np.nan)
    ax.imshow(
        np.where(np.isfinite(land), land, np.nan),
        origin="lower",
        extent=extent,
        cmap="Greys",
        vmin=-2,
        vmax=8,
        aspect="equal",
        alpha=0.35,
        interpolation="bilinear",
    )
    im = ax.imshow(
        np.where(depth > 0, depth, np.nan),
        origin="lower",
        extent=extent,
        cmap="Blues",
        vmin=0,
        vmax=max(2.0, slr),
        aspect="equal",
        interpolation="bilinear",
    )
    ax.plot(station["lon"], station["lat"], marker="*", color="#c0392b", markersize=12, markeredgecolor="white", markeredgewidth=0.7)
    ax.set_title(
        f"+{slr:.1f} m 相对 SLR\n全有效 {frac_all * 100:.1f}% | 低地 {frac_coast * 100:.1f}%",
        fontsize=8,
    )
    ax.set_xlabel("经度 °E")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="淹没水深 (m)")


def run_sensitivity(
    station_id: str,
    buffer_deg: float = 0.04,
    allow_synthetic: bool = False,
    dpi: int = 180,
) -> dict:
    cfg = load_config()
    stations = [s for s in cfg["stations"] if s["id"] == station_id]
    if not stations:
        raise ValueError(f"Unknown station {station_id}")

    st = stations[0]
    bbox = station_bbox(st, buffer_deg)
    lon2d, lat2d, elev, source, raster_meta, tile_files = load_dem(bbox, allow_synthetic=allow_synthetic)
    tile_list = tiles_for_bbox(bbox)
    valid = valid_mask(elev)
    coast = coastal_mask(elev, valid)
    stats = dem_stats(elev, valid)

    results = {
        "station_id": st["id"],
        "station_name": st["name"],
        "country": st.get("country", ""),
        "lat": st["lat"],
        "lon": st["lon"],
        "bbox": bbox,
        "dem_source": source,
        "tile_files": tile_files,
        "raster_meta": raster_meta,
        "deltadtm_tiles_in_bbox": int(len(tile_list)),
        "slr_levels_m": SLR_LEVELS,
        "dem_stats": stats,
        "flooded_fraction_all_valid": {},
        "flooded_fraction_coastal_lowland": {},
        "flooded_fraction": {},
    }

    is_synthetic = source.startswith("synthetic")
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(16, 5.8))
    gs = GridSpec(1, len(SLR_LEVELS) + 2, width_ratios=[1.25, 1, 1, 1, 0.85])
    ax_dem = fig.add_subplot(gs[0, 0])
    _plot_dem_panel(ax_dem, lon2d, lat2d, elev, valid, extent, st, source)

    for j, slr in enumerate(SLR_LEVELS):
        ax = fig.add_subplot(gs[0, j + 1])
        frac_all = flooded_fraction(elev, slr, valid)
        frac_coast = flooded_fraction(elev, slr, coast)
        results["flooded_fraction_all_valid"][str(slr)] = frac_all
        results["flooded_fraction_coastal_lowland"][str(slr)] = frac_coast
        results["flooded_fraction"][str(slr)] = frac_coast
        _plot_inundation_panel(ax, elev, valid, slr, extent, st, frac_all, frac_coast)

    ax_hist = fig.add_subplot(gs[0, -1])
    if stats:
        v = elev[valid]
        ax_hist.hist(v, bins=45, color="#2e86c1", edgecolor="white", linewidth=0.35, alpha=0.9)
        for slr in SLR_LEVELS:
            ax_hist.axvline(slr, color="#c0392b", ls="--", lw=1.0, alpha=0.85)
        ax_hist.set_xlabel("高程 (m EGM2008)")
        ax_hist.set_ylabel("像元数")
        ax_hist.set_title("高程分布\n(红虚线 = SLR 情景)", fontsize=8)
        ax_hist.grid(axis="y", alpha=0.25)

    title = f"{st['name']} ({st.get('country', '')}) — DeltaDTM 静态 SLR 淹没敏感性"
    if is_synthetic:
        title += " [合成 DEM，非真实地形]"
    fig.suptitle(title, fontsize=11, fontweight="bold", y=0.98)
    note = (
        "Bathtub: depth=max(0, SLR−DEM)；低地掩膜 elev≤15 m。"
        "DeltaDTM=EGM2008；SLR 为相对偏移，非完整垂直基准转换。"
        f" 瓦片: {', '.join(tile_files) or '无'}。"
    )
    if stats:
        note += f" 中位高程 {stats.get('elev_median_m', 0):.1f} m。"
    fig.text(0.5, 0.01, note, ha="center", fontsize=7, color="0.35")
    fig.tight_layout(rect=[0, 0.03, 1, 0.94])

    out_png = FIGURES / f"inundation_sensitivity_{st['id']}.png"
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    gj_path = PROCESSED / f"inundation_{st['id']}.geojson"
    gj_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"slr_m": slr, "flooded_fraction": results["flooded_fraction"][str(slr)]},
                        "geometry": {"type": "Polygon", "coordinates": [[[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]]]},
                    }
                    for slr in SLR_LEVELS
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    results["figure"] = str(out_png)
    results["geojson"] = str(gj_path)
    print(f"inundation -> {out_png} ({source})")
    return results


def run_batch(
    station_ids: list[str],
    buffer_deg: float = 0.04,
    allow_synthetic: bool = False,
    dpi: int = 180,
) -> list[dict]:
    all_results: list[dict] = []
    for sid in station_ids:
        try:
            all_results.append(run_sensitivity(sid, buffer_deg, allow_synthetic, dpi))
        except FileNotFoundError as exc:
            print(f"SKIP {sid}: {exc}")
    combined = PROCESSED / "inundation_sensitivity_all.json"
    combined.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    if all_results:
        PROCESSED / "inundation_sensitivity.json"
        (PROCESSED / "inundation_sensitivity.json").write_text(
            json.dumps(all_results[-1], indent=2),
            encoding="utf-8",
        )
    print(f"batch complete: {len(all_results)}/{len(station_ids)} stations -> {combined}")
    return all_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station-id", default=None, help="Single station id")
    parser.add_argument("--batch-eu", action="store_true", help="All European MVP stations with real tiles")
    parser.add_argument("--buffer-deg", type=float, default=0.04)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()
    ensure_dirs()

    if args.batch_eu:
        run_batch(sorted(EU_STATION_IDS), args.buffer_deg, args.allow_synthetic, args.dpi)
        return 0

    station_id = args.station_id or "sheerness-p015-uk"
    try:
        run_sensitivity(station_id, args.buffer_deg, args.allow_synthetic, args.dpi)
    except FileNotFoundError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

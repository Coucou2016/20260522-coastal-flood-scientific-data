#!/usr/bin/env python3
"""Build Communications Earth & Environment-style main figures.

The script uses only local, already processed project data and real DeltaDTM
GeoTIFF windows. It writes figure source CSV files so the manuscript figures are
auditable and can be regenerated without manual table copying.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import TwoSlopeNorm
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from inundation_sensitivity import coastal_mask, load_dem, station_bbox, valid_mask  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
FIG_MAIN = ROOT / "figures" / "main"
FIG_SUPP = ROOT / "figures" / "supplementary"
FIG_SOURCE = ROOT / "data" / "figure_source"
CONFIG = ROOT / "config" / "combo1_stations.yaml"
NATURAL_EARTH_URL = "https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_land.zip"
NATURAL_EARTH_DIR = ROOT / "data" / "raw" / "naturalearth" / "ne_110m_land"
TILE_CACHE = ROOT / "data" / "raw" / "map_tiles" / "carto_light_all"
TILE_URL = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"

EU_TERRAIN_IDS = {
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest-france",
}
EU_ORDER = [
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest-france",
]
OTHER_ORDER = ["newyork-the-battery", "hong-kong-b", "charleston-sc"]
SITE_LABELS = {
    "sheerness-p015-uk": "Sheerness",
    "newlyn-p001-uk": "Newlyn",
    "aberdeen-p038-uk": "Aberdeen",
    "hoekvanholla-hvh-nl": "Hoek van\nHolland",
    "brest-france": "Brest",
    "newyork-the-battery": "New York\n(The Battery)",
    "hong-kong-b": "Hong Kong",
    "charleston-sc": "Charleston",
}
SHORT_LABELS = {
    "sheerness-p015-uk": "Sheerness",
    "newlyn-p001-uk": "Newlyn",
    "aberdeen-p038-uk": "Aberdeen",
    "hoekvanholla-hvh-nl": "Hoek v.H.",
    "brest-france": "Brest",
    "newyork-the-battery": "New York",
    "hong-kong-b": "Hong Kong",
    "charleston-sc": "Charleston",
}


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "figure.titlesize": 12,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "savefig.facecolor": "white",
        }
    )


def ensure_dirs() -> None:
    FIG_MAIN.mkdir(parents=True, exist_ok=True)
    FIG_SUPP.mkdir(parents=True, exist_ok=True)
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)


def load_json(name: str):
    with (PROCESSED / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_stations() -> pd.DataFrame:
    with CONFIG.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    rows = []
    for s in cfg["stations"]:
        rows.append(
            {
                "station_id": s["id"],
                "station": s["name"],
                "country": s["country"],
                "lat": s["lat"],
                "lon": s["lon"],
                "terrain_screen": s["id"] in EU_TERRAIN_IDS,
            }
        )
    df = pd.DataFrame(rows)
    df["station_label"] = df["station_id"].map(SITE_LABELS)
    df["coordinate_label"] = df.apply(lambda r: f"{abs(r['lon']):.2f}{'E' if r['lon'] >= 0 else 'W'}, {abs(r['lat']):.2f}{'N' if r['lat'] >= 0 else 'S'}", axis=1)
    df.to_csv(FIG_SOURCE / "Fig1_station_metadata.csv", index=False)
    return df


def load_rp() -> pd.DataFrame:
    rp = pd.DataFrame(load_json("rp_comparison.json"))
    rp["D10_m"] = rp["coast_rp_rp10_m"] - rp["gssr_rp10_m"]
    rp["station"] = rp["station_id"].map(SHORT_LABELS)
    rp["group"] = np.where(rp["station_id"].isin(EU_ORDER), "Europe", "Non-European comparison")
    order = EU_ORDER + OTHER_ORDER
    rp["order"] = rp["station_id"].map({sid: i for i, sid in enumerate(order)})
    rp = rp.sort_values("order")
    rp[
        [
            "station_id",
            "station",
            "group",
            "gssr_rp10_m",
            "coast_rp_rp10_m",
            "D10_m",
            "match_dist_km",
        ]
    ].to_csv(FIG_SOURCE / "Fig2_water_level_divergence.csv", index=False)
    return rp


def load_corr() -> pd.DataFrame:
    summary = load_json("combo1_summary.json")
    corr = pd.DataFrame(summary["met_driver_correlations"])
    corr = corr.rename(
        columns={
            "spearman_surge_vs_pressure": "pressure",
            "spearman_surge_vs_wind": "wind",
            "spearman_surge_vs_precip": "precipitation",
        }
    )
    corr["station"] = corr["station_id"].map(SHORT_LABELS)
    corr = corr.sort_values("pressure")
    corr[["station_id", "station", "n_days", "pressure", "wind", "precipitation"]].to_csv(
        FIG_SOURCE / "Fig3_driver_correlations.csv", index=False
    )
    return corr


def load_terrain() -> pd.DataFrame:
    terrain = pd.DataFrame(load_json("inundation_sensitivity_all.json"))
    rows = []
    for _, r in terrain.iterrows():
        rows.append(
            {
                "station_id": r["station_id"],
                "station": SHORT_LABELS[r["station_id"]],
                "dem_source": r["dem_source"],
                "median_elev_m": r["dem_stats"]["elev_median_m"],
                "mean_elev_m": r["dem_stats"]["elev_mean_m"],
                "valid_fraction": r["dem_stats"]["valid_fraction"],
                "below_2m_all_valid_pct": 100 * r["dem_stats"]["elev_below_2m_fraction"],
                "flood_0p5_lowland_pct": 100 * r["flooded_fraction"]["0.5"],
                "flood_1p0_lowland_pct": 100 * r["flooded_fraction"]["1.0"],
                "flood_2p0_lowland_pct": 100 * r["flooded_fraction"]["2.0"],
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig4_terrain_sensitivity.csv", index=False)
    return out


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_MAIN / f"{stem}.png", dpi=450, bbox_inches="tight")
    fig.savefig(FIG_MAIN / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.08,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="bottom",
        ha="left",
    )


def natural_earth_land_shp() -> Path:
    shp = NATURAL_EARTH_DIR / "ne_110m_land.shp"
    if shp.exists():
        return shp
    NATURAL_EARTH_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = NATURAL_EARTH_DIR / "ne_110m_land.zip"
    if not zip_path.exists():
        urllib.request.urlretrieve(NATURAL_EARTH_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(NATURAL_EARTH_DIR)
    return shp


def lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    radius = 6378137.0
    lat = max(min(lat, 85.05112878), -85.05112878)
    x = radius * np.deg2rad(lon)
    y = radius * np.log(np.tan(np.pi / 4.0 + np.deg2rad(lat) / 2.0))
    return float(x), float(y)


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = int(np.floor((lon + 180.0) / 360.0 * n))
    y = int(np.floor((1.0 - np.log(np.tan(np.deg2rad(lat)) + 1.0 / np.cos(np.deg2rad(lat))) / np.pi) / 2.0 * n))
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def tile_bounds_mercator(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    n = 2**zoom
    lon_w = x / n * 360.0 - 180.0
    lon_e = (x + 1) / n * 360.0 - 180.0
    lat_n = np.rad2deg(np.arctan(np.sinh(np.pi * (1 - 2 * y / n))))
    lat_s = np.rad2deg(np.arctan(np.sinh(np.pi * (1 - 2 * (y + 1) / n))))
    xw, ys = lonlat_to_mercator(lon_w, lat_s)
    xe, yn = lonlat_to_mercator(lon_e, lat_n)
    return xw, xe, ys, yn


def fetch_tile(zoom: int, x: int, y: int) -> Path:
    path = TILE_CACHE / str(zoom) / str(x) / f"{y}.png"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = TILE_URL.format(z=zoom, x=x, y=y)
    request = urllib.request.Request(url, headers={"User-Agent": "coastal-flood-screening-paper/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        path.write_bytes(response.read())
    return path


def draw_tile_basemap(ax: plt.Axes, extent_lonlat: tuple[float, float, float, float], zoom: int) -> None:
    from PIL import Image

    west, east, south, north = extent_lonlat
    x0, y0 = lonlat_to_tile(west, north, zoom)
    x1, y1 = lonlat_to_tile(east, south, zoom)
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y0, y1), max(y0, y1) + 1)
    tile_size = 256
    mosaic = Image.new("RGB", (len(list(xs)) * tile_size, len(list(ys)) * tile_size), "#e8f1f7")
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y0, y1), max(y0, y1) + 1)
    for ix, tile_x in enumerate(xs):
        for iy, tile_y in enumerate(ys):
            tile_path = fetch_tile(zoom, tile_x, tile_y)
            tile = Image.open(tile_path).convert("RGB")
            mosaic.paste(tile, (ix * tile_size, iy * tile_size))
    left, _, _, top = tile_bounds_mercator(min(x0, x1), min(y0, y1), zoom)
    _, right, bottom, _ = tile_bounds_mercator(max(x0, x1), max(y0, y1), zoom)
    ax.imshow(mosaic, extent=[left, right, bottom, top], origin="upper", zorder=0)
    xmin, ymin = lonlat_to_mercator(west, south)
    xmax, ymax = lonlat_to_mercator(east, north)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("auto")
    ax.set_facecolor("#e8f1f7")
    lon_span = east - west
    lat_span = north - south
    lon_step = 60 if lon_span > 120 else 5 if lon_span > 20 else 2
    lat_step = 10 if lat_span > 25 else 2
    lon_ticks = np.arange(np.ceil(west / lon_step) * lon_step, east + 0.1, lon_step)
    lat_ticks = np.arange(np.ceil(south / lat_step) * lat_step, north + 0.1, lat_step)
    ax.set_xticks([lonlat_to_mercator(float(lon), 0)[0] for lon in lon_ticks])
    ax.set_xticklabels([f"{lon:g}" for lon in lon_ticks])
    ax.set_yticks([lonlat_to_mercator(0, float(lat))[1] for lat in lat_ticks])
    ax.set_yticklabels([f"{lat:g}" for lat in lat_ticks])
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.text(
        0.995,
        0.010,
        "Basemap: © OpenStreetMap contributors, © CARTO",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=5.5,
        color="#475569",
        bbox={"boxstyle": "round,pad=0.10", "fc": "white", "ec": "none", "alpha": 0.78},
        zorder=20,
    )


def draw_natural_earth_land(ax: plt.Axes, extent: tuple[float, float, float, float], lw: float = 0.38) -> None:
    import shapefile  # pyshp

    west, east, south, north = extent
    ax.set_facecolor("#e8f1f7")
    reader = shapefile.Reader(str(natural_earth_land_shp()))
    for shp in reader.shapes():
        minx, miny, maxx, maxy = shp.bbox
        if maxx < west or minx > east or maxy < south or miny > north:
            continue
        parts = list(shp.parts) + [len(shp.points)]
        for start, end in zip(parts[:-1], parts[1:]):
            pts = shp.points[start:end]
            if len(pts) < 3:
                continue
            ax.add_patch(
                Polygon(
                    pts,
                    closed=True,
                    facecolor="#d9e3d4",
                    edgecolor="#8ea08c",
                    lw=lw,
                    zorder=1,
                )
            )
    for lon in np.arange(np.ceil(west / 30) * 30, east + 1, 30):
        ax.axvline(lon, color="white", lw=0.5, zorder=0)
    for lat in np.arange(np.ceil(south / 10) * 10, north + 1, 10):
        ax.axhline(lat, color="white", lw=0.5, zorder=0)
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect("auto")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")


def label_station(ax: plt.Axes, row: pd.Series, dx: float, dy: float, fontsize: float = 6.7, show_coords: bool = True) -> None:
    label = SHORT_LABELS[row["station_id"]]
    if show_coords:
        label = f"{label}\n{row['coordinate_label']}"
    x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
    xt, yt = lonlat_to_mercator(float(row["lon"]) + dx, float(row["lat"]) + dy)
    ax.text(
        xt,
        yt,
        label,
        fontsize=fontsize,
        ha="left" if dx >= 0 else "right",
        va="center",
        color="#111827",
        zorder=8,
        linespacing=1.05,
        bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none", "alpha": 0.78},
    )


def annotate_station(ax: plt.Axes, row: pd.Series, x_text: float, y_text: float, fontsize: float = 6.6, show_coords: bool = True) -> None:
    label = SHORT_LABELS[row["station_id"]]
    if show_coords:
        label = f"{label}\n{row['coordinate_label']}"
    x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
    xt, yt = lonlat_to_mercator(x_text, y_text)
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(xt, yt),
        textcoords="data",
        ha="left",
        va="center",
        fontsize=fontsize,
        color="#111827",
        linespacing=1.05,
        arrowprops={"arrowstyle": "-", "color": "#475569", "lw": 0.55, "shrinkA": 2, "shrinkB": 2},
        bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none", "alpha": 0.82},
        zorder=9,
    )


def draw_station_points(ax: plt.Axes, stations: pd.DataFrame, size: float = 60, lw: float = 1.0) -> None:
    terrain = stations[stations["terrain_screen"]]
    no_terrain = stations[~stations["terrain_screen"]]
    ms = max(4.8, float(np.sqrt(size)))
    for k, (_, r) in enumerate(terrain.iterrows()):
        x, y = lonlat_to_mercator(float(r["lon"]), float(r["lat"]))
        ax.plot(
            x,
            y,
            marker="o",
            ms=ms,
            mfc="#1f78b4",
            mec="white",
            mew=lw,
            linestyle="None",
            label="Water-level + meteorology + DeltaDTM" if k == 0 else "_nolegend_",
            zorder=10,
        )
    for k, (_, r) in enumerate(no_terrain.iterrows()):
        x, y = lonlat_to_mercator(float(r["lon"]), float(r["lat"]))
        ax.plot(
            x,
            y,
            marker="o",
            ms=ms,
            mfc="white",
            mec="#1f78b4",
            mew=lw + 0.45,
            linestyle="None",
            label="Water-level + meteorology" if k == 0 else "_nolegend_",
            zorder=10,
        )


def draw_site_map(ax: plt.Axes, stations: pd.DataFrame) -> None:
    draw_tile_basemap(ax, (-130, 125, 15, 62), zoom=3)
    draw_station_points(ax, stations, size=72, lw=1.0)
    main_labels = {
        "newyork-the-battery": (-70.0, 43.5),
        "charleston-sc": (-70.0, 35.5),
        "hong-kong-b": (108.0, 27.5),
    }
    for _, r in stations.iterrows():
        if r["station_id"] in main_labels:
            x_text, y_text = main_labels[r["station_id"]]
            annotate_station(ax, r, x_text, y_text, fontsize=6.8, show_coords=True)
    rect_x0, rect_y0 = lonlat_to_mercator(-7.0, 47.0)
    rect_x1, rect_y1 = lonlat_to_mercator(6.5, 59.6)
    ax.add_patch(Rectangle((rect_x0, rect_y0), rect_x1 - rect_x0, rect_y1 - rect_y0, fill=False, edgecolor="#334155", lw=0.8, ls="--", zorder=4))
    text_x, text_y = lonlat_to_mercator(-6.5, 59.9)
    ax.text(text_x, text_y, "Europe inset", fontsize=6.7, color="#334155", ha="left", va="bottom", zorder=5)
    ax.legend(frameon=True, loc="lower left", framealpha=0.96, fontsize=7.1)
    ax.set_title("Tide-gauge sites on real-world coastal basemap", loc="left", fontweight="bold")
    panel_label(ax, "a")

    inset = ax.inset_axes([0.54, 0.13, 0.43, 0.77])
    draw_tile_basemap(inset, (-7.5, 7.0, 47.0, 59.8), zoom=5)
    eu = stations[stations["terrain_screen"]]
    draw_station_points(inset, eu, size=46, lw=0.85)
    eu_labels = {
        "aberdeen-p038-uk": (-0.8, 58.7),
        "hoekvanholla-hvh-nl": (4.9, 53.8),
        "sheerness-p015-uk": (2.6, 50.6),
        "newlyn-p001-uk": (-7.0, 51.1),
        "brest-france": (-7.0, 48.3),
    }
    for _, r in eu.iterrows():
        x_text, y_text = eu_labels[r["station_id"]]
        annotate_station(inset, r, x_text, y_text, fontsize=5.3, show_coords=True)
    inset.set_title("DeltaDTM terrain-screened European sites", loc="left", fontsize=6.4, fontweight="bold")
    inset.set_xlabel("")
    inset.set_ylabel("")
    inset.tick_params(labelsize=5.4)


def draw_data_coverage_matrix(ax: plt.Axes, stations: pd.DataFrame) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Data coverage and diagnostic role by site", loc="left", fontweight="bold", pad=2)
    panel_label(ax, "b")
    order = EU_ORDER + OTHER_ORDER
    rows = stations.set_index("station_id").loc[order].reset_index()
    cols = [
        ("GSSR\nsurge", "#14B8A6"),
        ("COAST-RP\nstorm tide", "#2563EB"),
        ("ERA5\nmeteo", "#84CC16"),
        ("DeltaDTM\nterrain", "#D97706"),
    ]
    x0 = 0.42
    xs = np.linspace(x0, 0.94, len(cols))
    y_top = 0.83
    y_step = 0.078
    ax.text(0.03, 0.90, "Station and coordinates", fontsize=7.2, fontweight="bold", color="#334155")
    for x, (name, color) in zip(xs, cols):
        ax.text(x, 0.90, name, ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#334155", linespacing=1.05)
        ax.plot([x, x], [0.16, 0.86], color="#E2E8F0", lw=0.6, zorder=0)
    for i, (_, r) in enumerate(rows.iterrows()):
        y = y_top - i * y_step
        is_eu = r["station_id"] in EU_TERRAIN_IDS
        ax.text(0.03, y, SHORT_LABELS[r["station_id"]], fontsize=7.0, ha="left", va="center", fontweight="bold" if is_eu else "normal")
        ax.text(0.19, y, r["coordinate_label"], fontsize=6.4, ha="left", va="center", color="#475569")
        availability = [True, True, True, bool(r["terrain_screen"])]
        for x, available, (_, color) in zip(xs, availability, cols):
            if available:
                ax.scatter([x], [y], s=58, color=color, edgecolor="white", lw=0.7, zorder=3)
            else:
                ax.scatter([x], [y], s=58, facecolor="white", edgecolor="#CBD5E1", lw=1.0, zorder=3)
        if i == len(EU_ORDER) - 1:
            ax.hlines(y - y_step / 2, 0.02, 0.97, color="#CBD5E1", lw=0.8)
    ax.text(
        0.03,
        0.07,
        "Filled symbols show data streams used for the present analysis. DeltaDTM terrain windows are available for the five European sites only.",
        fontsize=6.9,
        color="#475569",
        ha="left",
        va="bottom",
        wrap=True,
    )


def make_fig1(stations: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(13.2, 6.7))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.58, 1.0], wspace=0.18)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_matrix = fig.add_subplot(gs[0, 1])

    draw_site_map(ax_map, stations)
    draw_data_coverage_matrix(ax_matrix, stations)

    fig.suptitle("Study sites and data coverage for process-terrain coastal-flood screening", fontweight="bold", y=0.99)
    fig.subplots_adjust(top=0.88, left=0.055, right=0.985, bottom=0.10)
    fig.savefig(FIG_MAIN / "Fig1_process_terrain_design.png", dpi=450)
    fig.savefig(FIG_MAIN / "Fig1_process_terrain_design.pdf")
    plt.close(fig)


def make_fig2(rp: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(12, 5.7))
    gs = GridSpec(1, 3, figure=fig, width_ratios=[1.55, 1.25, 0.9], wspace=0.38)
    ax1, ax2, ax3 = [fig.add_subplot(gs[0, i]) for i in range(3)]

    x = np.arange(len(rp))
    w = 0.36
    ax1.bar(x - w / 2, rp["gssr_rp10_m"], width=w, color="#5eead4", edgecolor="#0f766e", label="GSSR RP10 surge")
    ax1.bar(x + w / 2, rp["coast_rp_rp10_m"], width=w, color="#93c5fd", edgecolor="#1d4ed8", label="COAST-RP RP10 storm tide")
    ax1.axvline(4.5, color="#64748b", lw=0.9, ls="--")
    ax1.text(2.0, 5.95, "European sites", ha="center", fontsize=8, color="#334155")
    ax1.text(6.0, 5.95, "Comparison sites", ha="center", fontsize=8, color="#334155")
    ax1.set_xticks(x)
    ax1.set_xticklabels(rp["station"], rotation=35, ha="right")
    ax1.set_ylabel("10-year indicator (m)")
    ax1.set_title("Paired water-level indicators", loc="left", fontweight="bold")
    ax1.legend(frameon=False, loc="upper right")
    ax1.grid(axis="y", color="#e2e8f0", lw=0.6)
    panel_label(ax1, "a")

    ranked = rp.sort_values("D10_m")
    colors = np.where(ranked["group"].eq("Europe"), "#2563eb", "#94a3b8")
    ax2.barh(ranked["station"], ranked["D10_m"], color=colors, edgecolor="white")
    ax2.set_xlabel("D10 = COAST-RP RP10 - GSSR RP10 (m)")
    ax2.set_title("Storm-tide minus surge divergence", loc="left", fontweight="bold")
    ax2.grid(axis="x", color="#e2e8f0", lw=0.6)
    for y, v in enumerate(ranked["D10_m"]):
        ax2.text(v + 0.05, y, f"{v:.2f}", va="center", fontsize=7.5)
    panel_label(ax2, "b")

    group_data = [rp.loc[rp["group"].eq("Europe"), "D10_m"], rp.loc[~rp["group"].eq("Europe"), "D10_m"]]
    for i, vals in enumerate(group_data):
        jitter = np.linspace(-0.05, 0.05, len(vals))
        ax3.scatter(np.full(len(vals), i) + jitter, vals, s=48, color=["#2563eb", "#64748b"][i], edgecolor="white", lw=0.8, zorder=3)
        ax3.hlines(vals.mean(), i - 0.22, i + 0.22, color="#111827", lw=2.0)
        ax3.text(i, vals.mean() + 0.18, f"mean {vals.mean():.2f} m", ha="center", fontsize=7.5)
    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(["Europe\n(n=5)", "Other\n(n=3)"])
    ax3.set_ylabel("D10 (m)")
    ax3.set_title("Descriptive regional contrast", loc="left", fontweight="bold")
    ax3.grid(axis="y", color="#e2e8f0", lw=0.6)
    ax3.text(0.02, 0.03, "No significance test;\nsmall screening sample.", transform=ax3.transAxes, fontsize=7.4, color="#475569")
    panel_label(ax3, "c")

    fig.suptitle("Surge-based and storm-tide-based indicators diverge by coastal setting", fontweight="bold", y=1.02)
    save_figure(fig, "Fig2_water_level_divergence")


def binned_series(df: pd.DataFrame, station_id: str, xcol: str, ycol: str, n_bins: int = 24) -> pd.DataFrame:
    sub = df[df["station_id"].eq(station_id)].copy()
    sub = sub[[xcol, ycol]].dropna()
    sub["bin"] = pd.qcut(sub[xcol], q=n_bins, duplicates="drop")
    out = sub.groupby("bin", observed=True).agg(
        x_mid=(xcol, "median"),
        y_med=(ycol, "median"),
        y_q25=(ycol, lambda s: s.quantile(0.25)),
        y_q75=(ycol, lambda s: s.quantile(0.75)),
        n=(ycol, "size"),
    )
    out["station_id"] = station_id
    return out.reset_index(drop=True)


def make_fig3(corr: pd.DataFrame) -> None:
    gssr = pd.read_parquet(PROCESSED / "gssr_daily_merged.parquet")
    drivers = pd.read_parquet(PROCESSED / "drivers_daily.parquet")
    daily = gssr.merge(drivers, on=["station_id", "date"], how="inner")
    daily.to_parquet(FIG_SOURCE / "Fig3_daily_merged_source.parquet", index=False)

    fig = plt.figure(figsize=(12, 5.8))
    gs = GridSpec(1, 3, figure=fig, width_ratios=[1.12, 1.05, 1.05], wspace=0.48)
    ax1, ax2, ax3 = [fig.add_subplot(gs[0, i]) for i in range(3)]

    heat = corr[["pressure", "wind", "precipitation"]].to_numpy()
    labels = corr["station"].to_list()
    im = ax1.imshow(heat, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1), aspect="auto")
    ax1.set_xticks([0, 1, 2])
    ax1.set_xticklabels(["Pressure", "Wind", "Precip."])
    ax1.set_yticks(np.arange(len(labels)))
    ax1.set_yticklabels(labels)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax1.text(j, i, f"{heat[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(heat[i, j]) > 0.55 else "#111827")
    ax1.set_title("Spearman rank correlation", loc="left", fontweight="bold")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.07)
    cbar.set_label("rho")
    panel_label(ax1, "a")

    for ax, sid, label in [(ax2, "newlyn-p001-uk", "Newlyn: extratropical coherence"), (ax3, "charleston-sc", "Charleston: weak daily-local coherence")]:
        sub = daily[daily["station_id"].eq(sid)]
        ax.scatter(sub["pressure_msl_min"], sub["surge_m"], s=4, color="#94a3b8", alpha=0.08, rasterized=True)
        b = binned_series(daily, sid, "pressure_msl_min", "surge_m", 24)
        b.to_csv(FIG_SOURCE / f"Fig3_{sid}_pressure_bins.csv", index=False)
        ax.plot(b["x_mid"], b["y_med"], color="#dc2626", lw=1.8, label="binned median")
        ax.fill_between(b["x_mid"], b["y_q25"], b["y_q75"], color="#fecaca", alpha=0.6, lw=0, label="IQR")
        rho = corr.loc[corr["station_id"].eq(sid), "pressure"].iloc[0]
        ax.set_title(label, loc="left", fontweight="bold")
        ax.set_xlabel("Daily minimum mean sea-level pressure (hPa)")
        ax.set_ylabel("GSSR daily surge (m)")
        ax.text(0.04, 0.92, f"rho = {rho:.3f}", transform=ax.transAxes, fontsize=8.5, bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#cbd5e1"})
        ax.grid(color="#e2e8f0", lw=0.6)
    ax2.legend(frameon=False, loc="upper right")
    panel_label(ax2, "b")
    panel_label(ax3, "c")

    fig.suptitle("Meteorological coherence of reconstructed daily surge is regime dependent", fontweight="bold", y=1.02)
    save_figure(fig, "Fig3_meteorological_coherence")


def _load_station_dem(station_row: dict, buffer_deg: float = 0.04):
    bbox = station_bbox(station_row, buffer_deg)
    lon2d, lat2d, elev, source, meta, tiles = load_dem(bbox, allow_synthetic=False)
    valid = valid_mask(elev)
    coast = coastal_mask(elev, valid)
    return bbox, lon2d, lat2d, elev, valid, coast, source, tiles


def _plot_terrain_map(ax: plt.Axes, station_row: dict, terrain_row: pd.Series, letter: str) -> None:
    bbox, _, _, elev, valid, _, source, _ = _load_station_dem(station_row)
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
    dem = np.where(valid, elev, np.nan)
    ax.imshow(dem, origin="lower", extent=extent, cmap="terrain", vmin=-2, vmax=16, aspect="equal", interpolation="bilinear")
    depth = np.where(valid, np.maximum(0.0, 2.0 - elev), np.nan)
    ax.imshow(np.where(depth > 0, depth, np.nan), origin="lower", extent=extent, cmap="Blues", vmin=0, vmax=2, aspect="equal", alpha=0.86)
    ax.plot(station_row["lon"], station_row["lat"], marker="*", ms=10, color="#b91c1c", mec="white", mew=0.7)
    ax.set_title(f"{station_row['station']}\n+2 m lowland {terrain_row['flood_2p0_lowland_pct']:.1f}%", loc="left", fontweight="bold", fontsize=8.5)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.tick_params(labelsize=6.5)
    panel_label(ax, letter)
    ax.text(0.02, 0.02, source.replace("DeltaDTM:", ""), transform=ax.transAxes, fontsize=6.4, color="#334155", bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "#cbd5e1", "alpha": 0.9})


def make_fig4(stations: pd.DataFrame, terrain: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(12.4, 10.5))
    gs = GridSpec(3, 3, figure=fig, height_ratios=[1, 1, 0.95], wspace=0.28, hspace=0.36)

    map_ids = ["sheerness-p015-uk", "hoekvanholla-hvh-nl", "brest-france", "newlyn-p001-uk", "aberdeen-p038-uk"]
    letters = ["a", "b", "c", "d", "e"]
    for idx, sid in enumerate(map_ids):
        ax = fig.add_subplot(gs[idx // 3, idx % 3])
        st = stations[stations["station_id"].eq(sid)].iloc[0].to_dict()
        tr = terrain[terrain["station_id"].eq(sid)].iloc[0]
        _plot_terrain_map(ax, st, tr, letters[idx])

    ax_hyp = fig.add_subplot(gs[1, 2])
    hyps_rows = []
    colors = {
        "sheerness-p015-uk": "#1d4ed8",
        "hoekvanholla-hvh-nl": "#0f766e",
        "brest-france": "#7c3aed",
        "newlyn-p001-uk": "#f97316",
        "aberdeen-p038-uk": "#64748b",
    }
    for sid in map_ids:
        st = stations[stations["station_id"].eq(sid)].iloc[0].to_dict()
        _, _, _, elev, valid, coast, _, _ = _load_station_dem(st)
        vals = elev[coast]
        vals = vals[np.isfinite(vals)]
        vals = vals[(vals > -10) & (vals <= 15)]
        if vals.size == 0:
            continue
        xs = np.linspace(-2, 15, 160)
        ys = np.array([(vals <= x).mean() for x in xs])
        hyps_rows.extend({"station_id": sid, "elevation_m": x, "cum_fraction": y} for x, y in zip(xs, ys))
        ax_hyp.plot(xs, ys * 100, color=colors[sid], lw=1.7, label=SHORT_LABELS[sid])
    pd.DataFrame(hyps_rows).to_csv(FIG_SOURCE / "Fig4_hypsometry_curves.csv", index=False)
    for level in [0.5, 1.0, 2.0]:
        ax_hyp.axvline(level, color="#111827", ls="--", lw=0.75, alpha=0.65)
    ax_hyp.set_xlim(-1, 12)
    ax_hyp.set_ylim(0, 105)
    ax_hyp.set_xlabel("DeltaDTM elevation (m)")
    ax_hyp.set_ylabel("Cumulative lowland fraction (%)")
    ax_hyp.set_title("Lowland hypsometry", loc="left", fontweight="bold")
    ax_hyp.grid(color="#e2e8f0", lw=0.6)
    ax_hyp.legend(frameon=False, fontsize=6.4, loc="lower right")
    panel_label(ax_hyp, "f")

    ax_bar = fig.add_subplot(gs[2, :])
    order = ["sheerness-p015-uk", "hoekvanholla-hvh-nl", "newlyn-p001-uk", "brest-france", "aberdeen-p038-uk"]
    t = terrain.set_index("station_id").loc[order].reset_index()
    x = np.arange(len(t))
    w = 0.23
    series = [("flood_0p5_lowland_pct", "+0.5 m", "#bfdbfe"), ("flood_1p0_lowland_pct", "+1.0 m", "#60a5fa"), ("flood_2p0_lowland_pct", "+2.0 m", "#1d4ed8")]
    for i, (col, label, color) in enumerate(series):
        ax_bar.bar(x + (i - 1) * w, t[col], width=w, label=label, color=color, edgecolor="white")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(t["station"])
    ax_bar.set_ylabel("Flooded fraction of coastal-lowland cells (%)")
    ax_bar.set_title("Static terrain sensitivity increases sharply only at lowland-dominated sites", loc="left", fontweight="bold")
    ax_bar.legend(frameon=False, ncol=3, loc="upper right")
    ax_bar.grid(axis="y", color="#e2e8f0", lw=0.6)
    panel_label(ax_bar, "g")

    fig.suptitle("DeltaDTM terrain sensitivity at five European coastal sites", fontweight="bold", y=0.995)
    fig.text(0.5, 0.01, "Maps show real DeltaDTM elevation with +2 m static terrain sensitivity overlay. No flood defences, connectivity, waves or river flow are included.", ha="center", fontsize=8, color="#475569")
    save_figure(fig, "Fig4_deltadtm_terrain_sensitivity")


def make_fig5(rp: pd.DataFrame, corr: pd.DataFrame, terrain: pd.DataFrame) -> None:
    merged = (
        terrain.merge(rp[["station_id", "D10_m", "coast_rp_rp10_m", "gssr_rp10_m"]], on="station_id", how="left")
        .merge(corr[["station_id", "pressure"]], on="station_id", how="left")
    )
    def classify(row):
        if row["flood_2p0_lowland_pct"] >= 20:
            return "water-level-terrain aligned hotspot"
        return "water-level-dominated but terrain-buffered"

    merged["typology_class"] = merged.apply(classify, axis=1)
    merged[
        [
            "station_id",
            "station",
            "D10_m",
            "pressure",
            "flood_2p0_lowland_pct",
            "median_elev_m",
            "typology_class",
        ]
    ].to_csv(FIG_SOURCE / "Fig5_process_terrain_typology.csv", index=False)

    fig = plt.figure(figsize=(12.2, 5.6))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.15, 1.0], wspace=0.32)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    ax1.axhspan(20, 50, color="#dbeafe", alpha=0.45, zorder=0)
    ax1.axhspan(0, 10, color="#f8fafc", alpha=1.0, zorder=0)
    sc = ax1.scatter(
        merged["D10_m"],
        merged["flood_2p0_lowland_pct"],
        c=merged["pressure"],
        s=130,
        cmap="RdBu_r",
        norm=TwoSlopeNorm(vmin=-0.9, vcenter=0, vmax=0.2),
        edgecolor="white",
        lw=0.9,
        zorder=3,
    )
    for _, r in merged.iterrows():
        dx = 0.04
        dy = 1.1
        if r["station_id"] == "hoekvanholla-hvh-nl":
            dy = -3.0
        ax1.text(r["D10_m"] + dx, r["flood_2p0_lowland_pct"] + dy, r["station"], fontsize=8)
    ax1.set_xlabel("D10 = storm-tide RP10 - surge RP10 (m)")
    ax1.set_ylabel("+2 m flooded lowland fraction (%)")
    ax1.set_xlim(1.55, 4.12)
    ax1.set_ylim(0, 48)
    ax1.set_title("Water-level divergence and terrain sensitivity", loc="left", fontweight="bold")
    ax1.grid(color="#e2e8f0", lw=0.6)
    ax1.text(1.62, 43.5, "aligned hotspots", color="#1d4ed8", fontsize=8.5, fontweight="bold")
    ax1.text(1.62, 5.2, "terrain-buffered", color="#475569", fontsize=8.5, fontweight="bold")
    cbar = fig.colorbar(sc, ax=ax1, fraction=0.046, pad=0.03)
    cbar.set_label("surge-pressure rho")
    panel_label(ax1, "a")

    ax2.axis("off")
    ax2.set_title("Process-terrain typology", loc="left", fontweight="bold")
    typologies = [
        ("Water-level-terrain aligned hotspots", "Sheerness; Hoek van Holland", "High +2 m lowland sensitivity;\nwater-level and terrain signals align.", "#dbeafe"),
        ("Water-level-dominated but terrain-buffered", "Brest; Newlyn; Aberdeen", "Large water-level divergence but\nlimited lowland response in the window.", "#fef3c7"),
        ("Process-diagnostic comparison sites", "New York; Charleston; Hong Kong", "Water-level and meteorological diagnostics only;\nadditional DeltaDTM packages needed.", "#f1f5f9"),
    ]
    y_positions = [0.70, 0.39, 0.10]
    for (title, sites, desc, color), y in zip(typologies, y_positions):
        ax2.add_patch(FancyBboxPatch((0.02, y), 0.96, 0.22, boxstyle="round,pad=0.02,rounding_size=0.025", facecolor=color, edgecolor="#94a3b8", lw=0.9))
        ax2.text(0.06, y + 0.165, title, ha="left", va="center", fontsize=9, fontweight="bold", color="#111827")
        ax2.text(0.06, y + 0.108, f"Sites: {sites}", ha="left", va="center", fontsize=8.2, color="#1f2937")
        ax2.text(0.06, y + 0.052, desc, ha="left", va="center", fontsize=7.7, color="#334155")
    panel_label(ax2, "b")

    fig.suptitle("Process-terrain typology of coastal flood susceptibility", fontweight="bold", y=1.02)
    save_figure(fig, "Fig5_process_terrain_typology")


def build_main_tables(rp: pd.DataFrame, corr: pd.DataFrame, terrain: pd.DataFrame) -> None:
    table1 = pd.DataFrame(
        [
            ["GSSR ERA5", "Daily reconstructed surge", "Tide-gauge station", "1979-2019 daily", "Station-scale surge variability and empirical return levels", "Residual/skew-surge-like metric, not total water level"],
            ["COAST-RP", "Storm-tide return level", "Global coastal point", "1-1000-year return periods", "Coastal storm-tide benchmark", "Includes tide; not directly equivalent to GSSR surge"],
            ["Open-Meteo ERA5", "Pressure, wind, precipitation", "Station-centred extraction", "1980-2010 daily summaries", "Atmospheric coherence screening", "Does not provide water levels"],
            ["DeltaDTM", "Terrain elevation", "~30 m coastal raster", "Static terrain", "Relative sea-level terrain sensitivity", "No hydrodynamics, connectivity, or defences"],
        ],
        columns=["Product", "Main variable used", "Spatial support", "Temporal or RP support", "Role in this study", "Main limitation"],
    )
    table1.to_csv(FIG_SOURCE / "Table1_data_products.csv", index=False)

    table2 = rp[
        ["station", "gssr_rp10_m", "coast_rp_rp10_m", "rp10_bias_m", "D10_m", "match_dist_km"]
    ].rename(
        columns={
            "station": "Station",
            "gssr_rp10_m": "GSSR RP10 surge (m)",
            "coast_rp_rp10_m": "COAST-RP RP10 storm tide (m)",
            "rp10_bias_m": "GSSR minus COAST-RP (m)",
            "D10_m": "Storm-tide minus surge (m)",
            "match_dist_km": "Match distance (km)",
        }
    )
    table2.to_csv(FIG_SOURCE / "Table2_water_level_indicators.csv", index=False)

    typology = pd.read_csv(FIG_SOURCE / "Fig5_process_terrain_typology.csv")
    table3 = typology.merge(
        rp[["station_id", "coast_rp_rp10_m", "gssr_rp10_m"]], on="station_id", how="left"
    )[
        ["station", "D10_m", "pressure", "flood_2p0_lowland_pct", "typology_class"]
    ].rename(
        columns={
            "station": "Station",
            "D10_m": "D10 storm-tide minus surge (m)",
            "pressure": "Surge-pressure rho",
            "flood_2p0_lowland_pct": "+2 m lowland sensitivity (%)",
            "typology_class": "Typology class",
        }
    )
    table3.to_csv(FIG_SOURCE / "Table3_process_terrain_typology.csv", index=False)

    terrain.rename(
        columns={
            "station": "Station",
            "dem_source": "DEM source",
            "median_elev_m": "Median elevation (m)",
            "valid_fraction": "Valid-cell fraction",
            "flood_0p5_lowland_pct": "Flooded lowland +0.5 m (%)",
            "flood_1p0_lowland_pct": "Flooded lowland +1.0 m (%)",
            "flood_2p0_lowland_pct": "Flooded lowland +2.0 m (%)",
        }
    ).to_csv(FIG_SOURCE / "Table4_deltadtm_sensitivity.csv", index=False)


def main() -> int:
    configure_style()
    ensure_dirs()
    stations = load_stations()
    rp = load_rp()
    corr = load_corr()
    terrain = load_terrain()

    make_fig1(stations)
    make_fig2(rp)
    make_fig3(corr)
    make_fig4(stations, terrain)
    make_fig5(rp, corr, terrain)
    build_main_tables(rp, corr, terrain)

    print(f"Wrote main figures to {FIG_MAIN}")
    print(f"Wrote figure source data to {FIG_SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

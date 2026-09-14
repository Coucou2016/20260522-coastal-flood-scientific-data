#!/usr/bin/env python3
"""Refined CEE-style figures with ocean-connected terrain sensitivity.

This script supersedes the first-pass figure composition. It keeps the same
output filenames in figures/main/ so the manuscript links remain stable, but
uses more polished layouts and an ocean-connected static inundation mask rather
than a non-connected bathtub mask.
"""

from __future__ import annotations

import json
import math
import sys
from collections import deque
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import BoundaryNorm, LightSource, LinearSegmentedColormap, LogNorm, TwoSlopeNorm
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from inundation_sensitivity import coastal_mask, load_dem, station_bbox, valid_mask  # noqa: E402
from make_cee_main_figures import draw_tile_basemap, lonlat_to_mercator  # noqa: E402
from publication_style import apply_publication_style  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "config" / "combo1_stations.yaml"
FIG_MAIN = ROOT / "figures" / "main"
FIG_SUPP = ROOT / "figures" / "supplementary"
FIG_SOURCE = ROOT / "data" / "figure_source"
OPEN_METEO_HOURLY = ROOT / "data" / "raw" / "open_meteo" / "hourly"

EU_TERRAIN_IDS = [
    "sheerness-p015-uk",
    "hoekvanholla-hvh-nl",
    "newlyn-p001-uk",
    "brest-france",
    "aberdeen-p038-uk",
]
EU_ORDER = [
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest-france",
]
OTHER_ORDER = ["newyork-the-battery", "hong-kong-b", "charleston-sc"]

# Approximate positive along-coast azimuths in degrees clockwise from north,
# used only to derive a diagnostic wind-stress proxy around annual maximum
# surge events. These are deliberately simple and are not used as predictors.
ALONGSHORE_AZIMUTH_DEG = {
    "sheerness-p015-uk": 90.0,
    "newlyn-p001-uk": 45.0,
    "aberdeen-p038-uk": 20.0,
    "hoekvanholla-hvh-nl": 45.0,
    "brest-france": 70.0,
    "newyork-the-battery": 20.0,
    "hong-kong-b": 90.0,
    "charleston-sc": 30.0,
}

SHORT = {
    "sheerness-p015-uk": "Sheerness",
    "newlyn-p001-uk": "Newlyn",
    "aberdeen-p038-uk": "Aberdeen",
    "hoekvanholla-hvh-nl": "Hoek v.H.",
    "brest-france": "Brest",
    "newyork-the-battery": "New York",
    "hong-kong-b": "Hong Kong",
    "charleston-sc": "Charleston",
}
FULL = {
    "sheerness-p015-uk": "Sheerness",
    "newlyn-p001-uk": "Newlyn",
    "aberdeen-p038-uk": "Aberdeen",
    "hoekvanholla-hvh-nl": "Hoek van Holland",
    "brest-france": "Brest",
    "newyork-the-battery": "New York-The Battery",
    "hong-kong-b": "Hong Kong",
    "charleston-sc": "Charleston",
}
PALETTE = {
    "surge": "#00A6A6",
    "storm": "#2F6BFF",
    "divergence": "#214E8A",
    "grey": "#7A869A",
    "lowland": "#0E7C7B",
    "hotspot": "#D1495B",
}

TIDAL_METADATA = {
    # Indicative mean spring tidal-range metadata used only as a regime context
    # diagnostic. Values should be source-verified against authoritative station
    # tide tables before journal submission.
    "sheerness-p015-uk": {"spring_tidal_range_m": 5.2, "tidal_regime": "macrotidal"},
    "newlyn-p001-uk": {"spring_tidal_range_m": 4.6, "tidal_regime": "macrotidal"},
    "aberdeen-p038-uk": {"spring_tidal_range_m": 3.5, "tidal_regime": "meso-macrotidal"},
    "hoekvanholla-hvh-nl": {"spring_tidal_range_m": 1.7, "tidal_regime": "mesotidal"},
    "brest-france": {"spring_tidal_range_m": 6.1, "tidal_regime": "macrotidal"},
    "newyork-the-battery": {"spring_tidal_range_m": 1.38, "tidal_regime": "mesotidal"},
    "hong-kong-b": {"spring_tidal_range_m": 1.9, "tidal_regime": "mesotidal"},
    "charleston-sc": {"spring_tidal_range_m": 1.591, "tidal_regime": "mesotidal"},
}


TERRAIN_CMAP = LinearSegmentedColormap.from_list(
    "muted_delta_terrain",
    ["#1f3b73", "#246b8e", "#2f9d7e", "#8ecf74", "#efe6ad", "#c9c1ad"],
)
TERRAIN_CMAP.set_bad("#eef3f7")
TERRAIN_CMAP.set_over("#ece8df")
NEUTRAL_TERRAIN_CMAP = LinearSegmentedColormap.from_list(
    "neutral_connectivity_terrain",
    ["#f8f7f4", "#e6dfd2", "#c8b89d", "#9b8b75", "#6f6358"],
)
NEUTRAL_TERRAIN_CMAP.set_bad("#e8f0f5")
NEUTRAL_TERRAIN_CMAP.set_over("#ede9e0")
FLOOD_CMAP = LinearSegmentedColormap.from_list("connected_flood", ["#cfefff", "#4ea3d8", "#08519c"])
FLOOD_CMAP.set_bad((1, 1, 1, 0))


def style() -> None:
    apply_publication_style()


def ensure_dirs() -> None:
    FIG_MAIN.mkdir(parents=True, exist_ok=True)
    FIG_SUPP.mkdir(parents=True, exist_ok=True)
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)


def panel(ax: plt.Axes, letter: str) -> None:
    ax.text(-0.08, 1.04, letter, transform=ax.transAxes, ha="left", va="bottom", fontsize=11, fontweight="bold")


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_MAIN / f"{stem}.png", dpi=500, bbox_inches="tight")
    fig.savefig(FIG_MAIN / f"{stem}.pdf", bbox_inches="tight")
    aliases = {
        "Fig5_process_terrain_typology": "Fig4_rank_discordance",
    }
    if stem in aliases:
        alias = aliases[stem]
        fig.savefig(FIG_MAIN / f"{alias}.png", dpi=500, bbox_inches="tight")
        fig.savefig(FIG_MAIN / f"{alias}.pdf", bbox_inches="tight")
    plt.close(fig)


def save_supp(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_SUPP / f"{stem}.png", dpi=500, bbox_inches="tight")
    fig.savefig(FIG_SUPP / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def load_json(name: str):
    with (PROCESSED / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def stations_df() -> pd.DataFrame:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows = []
    for s in cfg["stations"]:
        rows.append(
            {
                "station_id": s["id"],
                "station": s["name"],
                "label": SHORT[s["id"]],
                "country": s["country"],
                "lat": s["lat"],
                "lon": s["lon"],
                "terrain_screen": s["id"] in EU_TERRAIN_IDS,
            }
        )
    return pd.DataFrame(rows)


def gssr_empirical_rp_from_annual(annual_values: np.ndarray, rp_year: int = 10) -> float:
    annual = np.asarray(annual_values, dtype=float)
    annual = annual[np.isfinite(annual)]
    if annual.size < 5:
        return float("nan")
    ranked = np.sort(annual)
    n = len(ranked)
    nonexceedance = np.arange(1, n + 1, dtype=float) / (n + 1.0)
    target = 1.0 - 1.0 / float(rp_year)
    if target < nonexceedance[0] or target > nonexceedance[-1]:
        return float("nan")
    return float(np.interp(target, nonexceedance, ranked))


def gssr_rp10_bootstrap() -> pd.DataFrame:
    daily = pd.read_parquet(PROCESSED / "gssr_daily_merged.parquet")
    rows = []
    rng = np.random.default_rng(20260628)
    for sid, sub in daily.groupby("station_id"):
        annual = sub.groupby(sub["date"].dt.year)["surge_m"].max().dropna().to_numpy()
        reps = []
        if annual.size >= 5:
            for _ in range(2000):
                sample = rng.choice(annual, size=annual.size, replace=True)
                reps.append(gssr_empirical_rp_from_annual(sample, 10))
        reps = np.asarray(reps, dtype=float)
        rows.append(
            {
                "station_id": sid,
                "gssr_annual_max_years": int(annual.size),
                "gssr_rp10_bootstrap_p025_m": float(np.nanpercentile(reps, 2.5)) if reps.size else np.nan,
                "gssr_rp10_bootstrap_p500_m": float(np.nanpercentile(reps, 50.0)) if reps.size else np.nan,
                "gssr_rp10_bootstrap_p975_m": float(np.nanpercentile(reps, 97.5)) if reps.size else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig2_gssr_rp10_bootstrap.csv", index=False)
    return out


def haversine_km_array(lon1: float, lat1: float, lon2: np.ndarray, lat2: np.ndarray) -> np.ndarray:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = np.deg2rad(lat2)
    dlon = np.deg2rad(lon2 - lon1)
    dlat = p2 - p1
    a = np.sin(dlat / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def coast_rp_spatial_sensitivity(stations: pd.DataFrame) -> pd.DataFrame:
    import xarray as xr

    ds = xr.open_dataset(ROOT / "data" / "raw" / "coast_rp" / "extracted" / "COAST-RP.nc")
    lon = ds["station_x_coordinate"].values.astype(float)
    lat = ds["station_y_coordinate"].values.astype(float)
    rp10 = ds["storm_tide_rp_0010"].values.astype(float)
    rows = []
    for _, st in stations.iterrows():
        dist = haversine_km_array(float(st["lon"]), float(st["lat"]), lon, lat)
        order = np.argsort(dist)
        nearest3 = order[:3]
        within1 = order[dist[order] <= 1.0]
        within5 = order[dist[order] <= 5.0]
        rows.append(
            {
                "station_id": st["station_id"],
                "nearest_dist_km": float(dist[order[0]]),
                "nearest_rp10_m": float(rp10[order[0]]),
                "nearest3_mean_rp10_m": float(np.nanmean(rp10[nearest3])),
                "nearest3_min_rp10_m": float(np.nanmin(rp10[nearest3])),
                "nearest3_max_rp10_m": float(np.nanmax(rp10[nearest3])),
                "nearest3_range_m": float(np.nanmax(rp10[nearest3]) - np.nanmin(rp10[nearest3])),
                "within1km_n": int(len(within1)),
                "within1km_min_rp10_m": float(np.nanmin(rp10[within1])) if len(within1) else np.nan,
                "within1km_max_rp10_m": float(np.nanmax(rp10[within1])) if len(within1) else np.nan,
                "within5km_n": int(len(within5)),
                "within5km_min_rp10_m": float(np.nanmin(rp10[within5])) if len(within5) else np.nan,
                "within5km_max_rp10_m": float(np.nanmax(rp10[within5])) if len(within5) else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig2_coastrp_spatial_sensitivity.csv", index=False)
    return out


def tidal_metadata_df() -> pd.DataFrame:
    source_tracked = FIG_SOURCE / "Fig2_tidal_regime_metadata_source_verified.csv"
    if source_tracked.exists():
        out = pd.read_csv(source_tracked)
        out = out.drop(columns=["label"], errors="ignore")
        out["tidal_metadata_status"] = out["source_status"]
    else:
        out = pd.DataFrame.from_dict(TIDAL_METADATA, orient="index").reset_index(names="station_id")
        out["tidal_metadata_status"] = "fallback context; run scripts/build_tidal_metadata_sources.py for source tracking"
    out.to_csv(FIG_SOURCE / "Fig2_tidal_regime_metadata.csv", index=False)
    return out


def rp_df(stations: pd.DataFrame | None = None) -> pd.DataFrame:
    if stations is None:
        stations = stations_df()
    df = pd.DataFrame(load_json("rp_comparison.json"))
    df["D10_m"] = df["coast_rp_rp10_m"] - df["gssr_rp10_m"]
    df["label"] = df["station_id"].map(SHORT)
    df["full_label"] = df["station_id"].map(FULL)
    df["region"] = np.where(df["station_id"].isin(EU_ORDER), "Europe", "Comparison")
    df = df.merge(gssr_rp10_bootstrap(), on="station_id", how="left")
    df = df.merge(coast_rp_spatial_sensitivity(stations), on="station_id", how="left")
    df = df.merge(tidal_metadata_df(), on="station_id", how="left")
    order = EU_ORDER + OTHER_ORDER
    df["order"] = df["station_id"].map({sid: i for i, sid in enumerate(order)})
    df = df.sort_values("order").reset_index(drop=True)
    df[
        [
            "station_id",
            "full_label",
            "region",
            "gssr_rp10_m",
            "gssr_rp10_bootstrap_p025_m",
            "gssr_rp10_bootstrap_p975_m",
            "coast_rp_rp10_m",
            "nearest3_range_m",
            "within5km_n",
            "within5km_min_rp10_m",
            "within5km_max_rp10_m",
            "spring_tidal_range_m",
            "tidal_regime",
            "tidal_range_metric",
            "source_status",
            "D10_m",
            "match_dist_km",
        ]
    ].to_csv(FIG_SOURCE / "Fig2_water_level_divergence.csv", index=False)
    return df


def corr_df() -> pd.DataFrame:
    summary = load_json("combo1_summary.json")
    df = pd.DataFrame(summary["met_driver_correlations"]).rename(
        columns={
            "spearman_surge_vs_pressure": "pressure",
            "spearman_surge_vs_wind": "wind",
            "spearman_surge_vs_precip": "precipitation",
        }
    )
    df["label"] = df["station_id"].map(SHORT)
    df = df.sort_values("pressure").reset_index(drop=True)
    df["coherence_role"] = np.where(
        df["pressure"].le(-0.5),
        "pressure-coherent extratropical surge-process diagnostic",
        "weak or regime-dependent daily-local diagnostic",
    )
    df[["station_id", "label", "n_days", "pressure", "wind", "precipitation", "coherence_role"]].to_csv(
        FIG_SOURCE / "Fig3_driver_correlations.csv", index=False
    )
    return df


def short_extended_label(row: pd.Series) -> str:
    label = SHORT.get(str(row["station_id"]))
    if label:
        return label
    text = str(row.get("station", row["station_id"]))
    replacements = {
        " Van ": " v. ",
        " France": "",
        " Germany": "",
        " Denmark": "",
        " Norway": "",
        " P063 Uk": "",
        " P055 Uk": "",
        " P056 Uk": "",
        " P024 Uk": "",
        " P035 Uk": "",
        " P042 Uk": "",
        " P026 Uk": "",
        " P049 Uk": "",
        " P054 Uk": "",
        " P041 Uk": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text[:16]


def make_fig1(stations: pd.DataFrame) -> None:
    ext_path = FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv"
    diag_path = FIG_SOURCE / "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv"
    tide_path = FIG_SOURCE / "Fig5_tidal_metadata_coverage_summary.csv"
    ext = pd.read_csv(ext_path) if ext_path.exists() else pd.DataFrame()
    diag = None
    if diag_path.exists():
        diag_table = pd.read_csv(diag_path)
        diag_match = diag_table[
            diag_table["sample"].eq("primary resolved mask-aware match<=6km")
            & diag_table["terrain_metric"].eq("mask_connected_2m_lowland_pct")
        ]
        if not diag_match.empty:
            diag = diag_match.iloc[0]
    if not ext.empty:
        ext = ext[
            ext["marine_seed_resolved"].eq(True)
            & ext["match_dist_km"].le(6.0)
        ].dropna(subset=["coast_rp_rp10_m", "mask_connected_2m_lowland_pct"]).copy()
        ext["coast_rp_rank"] = ext["coast_rp_rp10_m"].rank(method="min", ascending=False).astype(int)
        ext["terrain_rank"] = ext["mask_connected_2m_lowland_pct"].rank(method="min", ascending=False).astype(int)
    top_n = int(diag["top_n"]) if diag is not None else max(1, int(math.ceil(0.2 * len(ext))))
    if not ext.empty:
        water_top = ext["coast_rp_rank"].le(top_n)
        terrain_top = ext["terrain_rank"].le(top_n)
        ext["priority_class"] = "other stations"
        ext.loc[water_top & ~terrain_top, "priority_class"] = "water-level top only"
        ext.loc[~water_top & terrain_top, "priority_class"] = "terrain top only"
        ext.loc[water_top & terrain_top, "priority_class"] = "top in both"

    fig = plt.figure(figsize=(13.0, 7.2))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1.15, 1.0], height_ratios=[1.0, 0.82], wspace=0.22, hspace=0.24)
    ax_focal = fig.add_subplot(gs[0, 0])
    ax_nw = fig.add_subplot(gs[:, 1])
    ax_cov = fig.add_subplot(gs[1, 0])

    draw_tile_basemap(ax_focal, (-130, 125, 15, 62), zoom=3)
    focal_colors = np.where(stations["terrain_screen"], "#174EA6", "white")
    for _, row in stations.iterrows():
        x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
        ax_focal.plot(
            x,
            y,
            marker="o",
            ms=7.8,
            mfc=focal_colors[row.name] if hasattr(focal_colors, "__len__") else "#174EA6",
            mec="#174EA6",
            mew=1.0,
            linestyle="None",
            zorder=5,
        )
    focal_labels = {
        "newyork-the-battery": (-70.0, 43.0),
        "charleston-sc": (-70.0, 34.0),
        "hong-kong-b": (105.0, 28.5),
        "sheerness-p015-uk": (12.0, 58.0),
    }
    for _, row in stations.iterrows():
        if row["station_id"] not in focal_labels:
            continue
        tx, ty = lonlat_to_mercator(*focal_labels[row["station_id"]])
        x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
        ax_focal.annotate(
            SHORT[row["station_id"]],
            xy=(x, y),
            xytext=(tx, ty),
            fontsize=7.0,
            ha="left",
            va="center",
            arrowprops={"arrowstyle": "-", "lw": 0.6, "color": "#475569"},
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.84},
            zorder=8,
        )
    x0, y0 = lonlat_to_mercator(-9, 47)
    x1, y1 = lonlat_to_mercator(9, 61)
    ax_focal.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="#111827", lw=1.0, ls="--", zorder=4))
    ax_focal.set_title("Focal gauges and Northwest Europe analysis window", loc="left", fontweight="bold")
    panel(ax_focal, "a")

    draw_tile_basemap(ax_nw, (-9.5, 9.5, 46.5, 61.5), zoom=5)
    class_style = {
        "other stations": {"marker": "o", "mfc": "#CBD5E1", "mec": "white", "ms": 5.2, "label": "Other primary stations"},
        "water-level top only": {"marker": "o", "mfc": "#D1495B", "mec": "white", "ms": 7.2, "label": "COAST-RP top only"},
        "terrain top only": {"marker": "s", "mfc": "#0E7C7B", "mec": "white", "ms": 7.0, "label": "Connected-terrain top only"},
        "top in both": {"marker": "*", "mfc": "#F59E0B", "mec": "#111827", "ms": 10.0, "label": "Top in both"},
    }
    if not ext.empty:
        for cls, style_dict in class_style.items():
            sub = ext[ext["priority_class"].eq(cls)]
            for _, row in sub.iterrows():
                x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
                ax_nw.plot(
                    x,
                    y,
                    marker=style_dict["marker"],
                    ms=style_dict["ms"],
                    mfc=style_dict["mfc"],
                    mec=style_dict["mec"],
                    mew=0.8,
                    linestyle="None",
                    label=style_dict["label"] if _ == sub.index[0] else "_nolegend_",
                    zorder=8 if cls != "other stations" else 5,
                )
        label_offsets = {
            "sheerness-p015-uk": (30_000, 18_000),
            "newport-p057-uk": (30_000, 18_000),
            "denhelder-hel-nl": (30_000, 18_000),
        }
        label_text = {
            "sheerness-p015-uk": "Sheerness",
            "newport-p057-uk": "Newport",
            "denhelder-hel-nl": "Den Helder",
        }
        label_rows = ext[ext["station_id"].isin(label_offsets)].copy()
        for _, row in label_rows.iterrows():
            x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
            dx, dy = label_offsets[str(row["station_id"])]
            ax_nw.text(
                x + dx,
                y + dy,
                label_text[str(row["station_id"])],
                fontsize=6.1,
                color="#111827",
                bbox={"boxstyle": "round,pad=0.08", "fc": "white", "ec": "none", "alpha": 0.76},
                zorder=10,
            )
    ax_nw.set_title("Primary 68-station sample and top-20% screening sets", loc="left", fontweight="bold")
    if diag is not None:
        ax_nw.text(
            0.02,
            0.03,
            f"Top-20% overlap {int(diag['top_overlap'])}/{top_n}; "
            f"descriptive mismatch {float(diag['top_mismatch']):.0%}\n"
            f"random expectation {float(diag['random_expected_mismatch']):.0%}",
            transform=ax_nw.transAxes,
            fontsize=8.0,
            color="#334155",
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#CBD5E1", "alpha": 0.92},
            zorder=20,
        )
    ax_nw.legend(frameon=True, loc="upper right", fontsize=6.7, framealpha=0.95)
    panel(ax_nw, "b")

    ax_cov.axis("off")
    ax_cov.set_title("Data coverage and diagnostic role", loc="left", fontweight="bold")
    panel(ax_cov, "c")
    tide_counts = {}
    if tide_path.exists():
        tide = pd.read_csv(tide_path)
        tide_counts = dict(zip(tide["source_status"], tide["n_sites"]))
    rows = [
        ("Focal gauges", "8", ["8", "8", "8", "5 detailed", "5 verified", "process QC"]),
        ("Primary regional", "68", ["not required", "68", "-", "68 +2 m", "not required", "rank + block"]),
        ("Distance sensitivity", "74", ["not required", "74", "-", "74 +2 m", "not required", "match audit"]),
        ("GSSR-qualified", "44", ["44", "44", "-", "44 +2 m", f"{int(tide_counts.get('source_verified', 0))} verified", "sample check"]),
    ]
    cols = ["GSSR", "COAST-RP", "ERA5", "DeltaDTM", "Tide meta", "Robustness"]
    ax_cov.text(0.02, 0.78, "Set", fontsize=7.2, fontweight="bold", color="#334155")
    ax_cov.text(0.25, 0.78, "n", fontsize=7.2, fontweight="bold", color="#334155")
    x_cols = np.linspace(0.40, 0.93, len(cols))
    for x, col in zip(x_cols, cols):
        ax_cov.text(x, 0.78, col, fontsize=6.9, ha="center", va="bottom", fontweight="bold", color="#334155")
    y0 = 0.64
    for i, (name, n, vals) in enumerate(rows):
        y = y0 - i * 0.14
        ax_cov.text(0.02, y, name, fontsize=7.2, ha="left", va="center")
        ax_cov.text(0.26, y, n, fontsize=7.2, ha="center", va="center", color="#334155")
        for x, val in zip(x_cols, vals):
            color = "#E0F2FE" if val not in {"-", ""} else "#F1F5F9"
            edge = "#38BDF8" if val not in {"-", ""} else "#CBD5E1"
            ax_cov.add_patch(Rectangle((x - 0.045, y - 0.045), 0.09, 0.09, facecolor=color, edgecolor=edge, lw=0.8))
            ax_cov.text(x, y, val, fontsize=6.1, ha="center", va="center", color="#0F172A")
    ax_cov.text(
        0.02,
        0.06,
        "Primary analysis: resolved official-mask marine seed and COAST-RP match <= 6 km. Broader and GSSR-qualified sets are sensitivities.",
        fontsize=6.8,
        color="#475569",
        ha="left",
        va="bottom",
        wrap=True,
    )

    fig.subplots_adjust(top=0.965, left=0.055, right=0.985, bottom=0.075)
    save(fig, "Fig1_process_terrain_design")


def neighbour_offsets(connectivity: int = 8) -> list[tuple[int, int]]:
    if connectivity == 4:
        return [(-1, 0), (0, -1), (0, 1), (1, 0)]
    if connectivity == 8:
        return [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    raise ValueError("connectivity must be 4 or 8")


def boundary_ocean_seed(valid: np.ndarray) -> np.ndarray:
    """Boundary water/no-data cells used as explicit marine seed cells."""
    ocean = ~valid
    seed = np.zeros(ocean.shape, dtype=bool)
    if ocean.size == 0:
        return seed
    seed[0, :] = ocean[0, :]
    seed[-1, :] = ocean[-1, :]
    seed[:, 0] |= ocean[:, 0]
    seed[:, -1] |= ocean[:, -1]
    return seed


def flood_fill(mask: np.ndarray, seed: np.ndarray, connectivity: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Return cells in mask reachable from seed and shortest grid distance."""
    visited = np.zeros(mask.shape, dtype=bool)
    distance = np.full(mask.shape, -1, dtype=np.int32)
    q: deque[tuple[int, int]] = deque()
    h, w = mask.shape
    for i, j in np.argwhere(seed & mask):
        visited[i, j] = True
        distance[i, j] = 0
        q.append((int(i), int(j)))
    if not q:
        return visited, distance
    neighbours = neighbour_offsets(connectivity)
    while q:
        i, j = q.popleft()
        for di, dj in neighbours:
            ni, nj = i + di, j + dj
            if 0 <= ni < h and 0 <= nj < w and mask[ni, nj] and not visited[ni, nj]:
                visited[ni, nj] = True
                distance[ni, nj] = distance[i, j] + 1
                q.append((ni, nj))
    return visited, distance


def flood_connectivity_layers(
    elev: np.ndarray,
    valid: np.ndarray,
    eta: float,
    connectivity: int = 8,
) -> dict[str, np.ndarray]:
    """Static below-level layers after boundary-seeded marine connectivity filtering."""
    low = valid & np.isfinite(elev) & (elev <= eta)
    ocean = ~valid
    seed = boundary_ocean_seed(valid)
    ocean_reachable, _ = flood_fill(ocean, seed, connectivity=connectivity)
    passable = low | ocean_reachable
    reachable, distance = flood_fill(passable, seed, connectivity=connectivity)
    connected = reachable & low
    return {
        "low": low,
        "ocean": ocean,
        "seed": seed,
        "ocean_reachable": ocean_reachable,
        "passable": passable,
        "reachable": reachable,
        "connected": connected,
        "unconnected": low & ~connected,
        "distance": distance,
    }


def flood_connected_mask(elev: np.ndarray, valid: np.ndarray, eta: float, connectivity: int = 8) -> np.ndarray:
    """Cells below eta connected to a boundary-linked ocean/water component."""
    return flood_connectivity_layers(elev, valid, eta, connectivity=connectivity)["connected"]


def connected_components(mask: np.ndarray, connectivity: int = 8) -> tuple[np.ndarray, list[dict[str, int]]]:
    """Connected-component labels and area metrics for a boolean mask."""
    labels = np.zeros(mask.shape, dtype=np.int32)
    components: list[dict[str, int]] = []
    neighbours = neighbour_offsets(connectivity)
    h, w = mask.shape
    component_id = 0
    for si, sj in np.argwhere(mask):
        si, sj = int(si), int(sj)
        if labels[si, sj] != 0:
            continue
        component_id += 1
        q: deque[tuple[int, int]] = deque([(si, sj)])
        labels[si, sj] = component_id
        cells = 0
        while q:
            i, j = q.popleft()
            cells += 1
            for di, dj in neighbours:
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and mask[ni, nj] and labels[ni, nj] == 0:
                    labels[ni, nj] = component_id
                    q.append((ni, nj))
        components.append({"component_id": component_id, "cells": cells})
    components.sort(key=lambda r: r["cells"], reverse=True)
    return labels, components


def grid_step_km(lon2d: np.ndarray, lat2d: np.ndarray) -> float:
    lat0 = float(np.nanmedian(lat2d))
    dx = float(np.nanmedian(np.abs(np.diff(lon2d, axis=1)))) * 111.32 * np.cos(np.deg2rad(lat0))
    dy = float(np.nanmedian(np.abs(np.diff(lat2d, axis=0)))) * 111.32
    vals = [v for v in [dx, dy] if np.isfinite(v) and v > 0]
    return float(np.mean(vals)) if vals else 0.03


def station_dem(station_row: pd.Series, buffer_deg: float = 0.04):
    st = {
        "id": station_row["station_id"],
        "name": station_row["station"],
        "country": station_row["country"],
        "lat": float(station_row["lat"]),
        "lon": float(station_row["lon"]),
    }
    bbox = station_bbox(st, buffer_deg)
    lon2d, lat2d, elev, source, meta, tiles = load_dem(bbox, allow_synthetic=False)
    valid = valid_mask(elev)
    coast = coastal_mask(elev, valid)
    return st, bbox, lon2d, lat2d, elev, valid, coast, source, tiles


def connected_terrain_df(stations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    audit_rows = []
    component_rows = []
    dem_error_rows = []
    for sid in EU_TERRAIN_IDS:
        row = stations.loc[stations["station_id"].eq(sid)].iloc[0]
        _, _, lon2d, lat2d, elev, valid, coast, source, tiles = station_dem(row)
        vals = elev[valid]
        low_vals = elev[coast]
        denom = int(coast.sum())
        cell_km = grid_step_km(lon2d, lat2d)
        result = {
            "station_id": sid,
            "label": SHORT[sid],
            "full_label": FULL[sid],
            "dem_source": source,
            "tiles": ";".join(tiles),
            "valid_fraction": float(valid.mean()),
            "median_elev_m": float(np.nanmedian(vals)),
            "median_lowland_elev_m": float(np.nanmedian(low_vals)),
            "coastal_lowland_cells": denom,
            "approx_cell_step_km": cell_km,
        }
        for eta in [0.5, 1.0, 2.0]:
            layers8 = flood_connectivity_layers(elev, valid, eta, connectivity=8)
            layers4 = flood_connectivity_layers(elev, valid, eta, connectivity=4)
            below = layers8["low"] & coast
            connected8 = layers8["connected"] & coast
            connected4 = layers4["connected"] & coast
            unconnected8 = below & ~connected8
            below_cells = int(below.sum())
            connected8_cells = int(connected8.sum())
            connected4_cells = int(connected4.sum())
            unconnected8_cells = int(unconnected8.sum())
            below_pct = float(100 * below_cells / denom) if denom else 0.0
            connected8_pct = float(100 * connected8_cells / denom) if denom else 0.0
            connected4_pct = float(100 * connected4_cells / denom) if denom else 0.0
            unconnected8_pct = float(100 * unconnected8_cells / denom) if denom else 0.0
            result[f"connected_{eta:g}m_lowland_pct"] = connected8_pct
            result[f"connected4_{eta:g}m_lowland_pct"] = connected4_pct
            result[f"unconnected_{eta:g}m_lowland_pct"] = unconnected8_pct
            result[f"bathtub_{eta:g}m_lowland_pct"] = below_pct
            dist8 = layers8["distance"]
            d_conn = dist8[connected8]
            d_conn = d_conn[d_conn >= 0]
            audit_rows.append(
                {
                    "station_id": sid,
                    "label": SHORT[sid],
                    "eta_m": eta,
                    "coastal_lowland_cells": denom,
                    "all_below_cells": below_cells,
                    "connected8_cells": connected8_cells,
                    "connected4_cells": connected4_cells,
                    "unconnected8_cells": unconnected8_cells,
                    "seed_cells": int(layers8["seed"].sum()),
                    "boundary_linked_ocean_cells_8n": int(layers8["ocean_reachable"].sum()),
                    "all_below_lowland_pct": below_pct,
                    "connected8_lowland_pct": connected8_pct,
                    "connected4_lowland_pct": connected4_pct,
                    "unconnected8_lowland_pct": unconnected8_pct,
                    "connected4_minus_connected8_pct_points": connected4_pct - connected8_pct,
                    "connected4_to_connected8_ratio": float(connected4_pct / connected8_pct) if connected8_pct > 0 else np.nan,
                    "max_path_steps_8n": int(d_conn.max()) if d_conn.size else 0,
                    "p95_path_steps_8n": float(np.nanpercentile(d_conn, 95)) if d_conn.size else 0.0,
                    "max_path_km_8n": float(d_conn.max() * cell_km) if d_conn.size else 0.0,
                    "p95_path_km_8n": float(np.nanpercentile(d_conn, 95) * cell_km) if d_conn.size else 0.0,
                }
            )
            if eta == 2.0:
                dem_shift_pcts = {}
                for dem_shift in [-1.0, -0.5, 0.0, 0.5, 1.0]:
                    shifted_layers = flood_connectivity_layers(elev + dem_shift, valid, eta, connectivity=8)
                    shifted_connected = shifted_layers["connected"] & coast
                    shifted_pct = float(100 * shifted_connected.sum() / denom) if denom else 0.0
                    dem_shift_pcts[dem_shift] = shifted_pct
                    dem_error_rows.append(
                        {
                            "station_id": sid,
                            "label": SHORT[sid],
                            "eta_m": eta,
                            "dem_vertical_shift_m": dem_shift,
                            "connected8_lowland_pct": shifted_pct,
                        }
                    )
                result["connected_2m_dem_shift_m1_pct"] = dem_shift_pcts[-1.0]
                result["connected_2m_dem_shift_m05_pct"] = dem_shift_pcts[-0.5]
                result["connected_2m_dem_shift_0_pct"] = dem_shift_pcts[0.0]
                result["connected_2m_dem_shift_p05_pct"] = dem_shift_pcts[0.5]
                result["connected_2m_dem_shift_p1_pct"] = dem_shift_pcts[1.0]
                result["connected_2m_dem_pm05_min_pct"] = min(dem_shift_pcts[-0.5], dem_shift_pcts[0.5])
                result["connected_2m_dem_pm05_max_pct"] = max(dem_shift_pcts[-0.5], dem_shift_pcts[0.5])
                result["connected_2m_dem_pm1_min_pct"] = min(dem_shift_pcts[-1.0], dem_shift_pcts[1.0])
                result["connected_2m_dem_pm1_max_pct"] = max(dem_shift_pcts[-1.0], dem_shift_pcts[1.0])
                for conn_rule, layers, connected_mask in [
                    ("8-neighbour", layers8, connected8),
                    ("4-neighbour", layers4, connected4),
                ]:
                    labels, components = connected_components(connected_mask, connectivity=8 if conn_rule == "8-neighbour" else 4)
                    dist = layers["distance"]
                    for comp in components:
                        cmask = labels == comp["component_id"]
                        d = dist[cmask]
                        d = d[d >= 0]
                        component_rows.append(
                            {
                                "station_id": sid,
                                "label": SHORT[sid],
                                "connectivity_rule": conn_rule,
                                "eta_m": eta,
                                "component_id": comp["component_id"],
                                "area_cells": comp["cells"],
                                "area_lowland_pct": float(100 * comp["cells"] / denom) if denom else 0.0,
                                "mean_path_steps": float(np.nanmean(d)) if d.size else 0.0,
                                "p95_path_steps": float(np.nanpercentile(d, 95)) if d.size else 0.0,
                                "max_path_steps": int(d.max()) if d.size else 0,
                                "mean_path_km": float(np.nanmean(d) * cell_km) if d.size else 0.0,
                                "p95_path_km": float(np.nanpercentile(d, 95) * cell_km) if d.size else 0.0,
                                "max_path_km": float(d.max() * cell_km) if d.size else 0.0,
                            }
                        )
        rows.append(result)
    out = pd.DataFrame(rows)
    for eta in [0.5, 1.0, 2.0]:
        assert (out[f"connected_{eta:g}m_lowland_pct"] <= out[f"bathtub_{eta:g}m_lowland_pct"] + 1e-9).all()
        assert (out[f"connected4_{eta:g}m_lowland_pct"] <= out[f"bathtub_{eta:g}m_lowland_pct"] + 1e-9).all()
    assert out["dem_source"].str.startswith("DeltaDTM").all()
    out.to_csv(FIG_SOURCE / "Fig4_connected_terrain_sensitivity.csv", index=False)
    audit = pd.DataFrame(audit_rows)
    components = pd.DataFrame(component_rows)
    dem_errors = pd.DataFrame(dem_error_rows)
    audit.to_csv(FIG_SOURCE / "Fig4_connectivity_audit_summary.csv", index=False)
    components.to_csv(FIG_SOURCE / "Fig4_connectivity_component_metrics.csv", index=False)
    dem_errors.to_csv(FIG_SOURCE / "Fig4_dem_error_ensemble.csv", index=False)
    write_fig4_audit_report(out, audit, components)
    return out


def write_fig4_audit_report(terrain: pd.DataFrame, audit: pd.DataFrame, components: pd.DataFrame) -> None:
    rows = audit[audit["eta_m"].eq(2.0)].copy()
    rows = rows.sort_values("connected8_lowland_pct", ascending=False)
    lines = [
        "# Figure 3 connectivity audit",
        "",
        "This file is generated by `scripts/make_cee_refined_figures.py` from the local DeltaDTM windows.",
        "The main terrain metric uses an eight-neighbour flood fill from boundary-linked ocean/water cells. A four-neighbour sensitivity is stored alongside it to diagnose diagonal-pixel leakage.",
        "Interior no-data components are not seeded unless they are connected to the boundary-linked ocean/water component.",
        "",
        "## +2 m site summary",
        "",
        "| Station | All below +2 m (%) | Connected 8-neighbour (%) | Connected 4-neighbour (%) | Unconnected below +2 m (%) | 4n - 8n (pct points) | P95 path length 8n (km) | Max path length 8n (km) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in rows.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    r["label"],
                    f"{r['all_below_lowland_pct']:.2f}",
                    f"{r['connected8_lowland_pct']:.2f}",
                    f"{r['connected4_lowland_pct']:.2f}",
                    f"{r['unconnected8_lowland_pct']:.2f}",
                    f"{r['connected4_minus_connected8_pct_points']:.2f}",
                    f"{r['p95_path_km_8n']:.2f}",
                    f"{r['max_path_km_8n']:.2f}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Largest +2 m connected components",
            "",
            "| Station | Rule | Component ID | Area cells | Area lowland (%) | P95 path (km) | Max path (km) |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    if not components.empty:
        top_components = (
            components.sort_values(["station_id", "connectivity_rule", "area_cells"], ascending=[True, True, False])
            .groupby(["station_id", "connectivity_rule"], as_index=False)
            .head(3)
        )
        for _, r in top_components.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        r["label"],
                        r["connectivity_rule"],
                        str(int(r["component_id"])),
                        str(int(r["area_cells"])),
                        f"{r['area_lowland_pct']:.2f}",
                        f"{r['p95_path_km']:.2f}",
                        f"{r['max_path_km']:.2f}",
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- The connected layer is a static terrain-sensitivity screen, not a dynamic flood forecast.",
            "- Blue Figure 3 pixels are connected static water-depth candidates computed as h=max(0, eta-z) after boundary-linked connectivity filtering.",
            "- Orange audit pixels are below the +2 m level but excluded from the connected metric because they are not linked to the marine seed under the stated rule.",
            "- The four-neighbour result is not used as the primary result; it tests whether diagonal-only contacts materially affect the conclusion.",
        ]
    )
    (FIG_SOURCE / "Fig4_connectivity_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_fig2(rp: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(12.8, 5.2), layout="constrained")
    gs = GridSpec(1, 3, width_ratios=[1.55, 1.00, 0.98], wspace=0.28, figure=fig)
    ax0, ax1, ax2 = [fig.add_subplot(gs[0, i]) for i in range(3)]

    y = np.arange(len(rp))[::-1]
    # Subtle group background.
    ax0.axhspan(3.5, 7.5, color="#EEF6FF", zorder=0)
    ax0.axhspan(-0.5, 2.5, color="#F7F8FA", zorder=0)
    for yi, (_, r) in zip(y, rp.iterrows()):
        ax0.plot([r["gssr_rp10_m"], r["coast_rp_rp10_m"]], [yi, yi], color="#CBD5E1", lw=6, solid_capstyle="round", zorder=1)
        ax0.plot([r["gssr_rp10_m"], r["coast_rp_rp10_m"]], [yi, yi], color="#64748B", lw=1.0, zorder=2)
    ax0.scatter(rp["gssr_rp10_m"], y, s=55, color=PALETTE["surge"], edgecolor="white", lw=0.8, label="GSSR RP10 surge", zorder=3)
    ax0.scatter(rp["coast_rp_rp10_m"], y, s=55, color=PALETTE["storm"], edgecolor="white", lw=0.8, label="COAST-RP RP10 storm tide", zorder=3)
    ax0.set_yticks(y)
    ax0.set_yticklabels(rp["full_label"])
    ax0.set_xlabel("10-year water-level indicator (m)")
    ax0.set_title("Paired indicators at matched coastal sites", loc="left", fontweight="bold")
    ax0.grid(axis="x", color="#E2E8F0", lw=0.6)
    ax0.legend(frameon=False, loc="lower right", ncol=1)
    ax0.text(0.02, 0.95, "Europe", transform=ax0.transAxes, color="#245B9A", fontweight="bold")
    ax0.text(0.02, 0.30, "comparison sites", transform=ax0.transAxes, color="#64748B", fontweight="bold")
    panel(ax0, "a")

    ranked = rp.sort_values("D10_m", ascending=True)
    yy = np.arange(len(ranked))
    colors = np.where(ranked["region"].eq("Europe"), PALETTE["divergence"], "#9AA7B8")
    ax1.barh(yy, ranked["D10_m"], color=colors, height=0.62)
    ax1.set_yticks(yy)
    ax1.set_yticklabels(ranked["label"])
    ax1.set_xlabel(r"$D_{10}$ = storm tide - surge (m)")
    ax1.set_title("Product-definition divergence", loc="left", fontweight="bold")
    ax1.grid(axis="x", color="#E2E8F0", lw=0.6)
    for i, v in enumerate(ranked["D10_m"]):
        ax1.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=7.3)
    panel(ax1, "b")

    for region, color, marker, label in [
        ("Europe", "#2F6BFF", "o", "European focal sites"),
        ("Comparison", "#7A869A", "s", "Comparison sites"),
    ]:
        sub = rp[rp["region"].eq(region)]
        for status, status_sub in sub.groupby(sub["source_status"].eq("source_verified")):
            ax2.scatter(
                status_sub["spring_tidal_range_m"],
                status_sub["D10_m"],
                s=54,
                facecolor=color if status else "white",
                marker=marker,
                edgecolor=color,
                lw=1.0,
                label=label if status else f"{label}, contextual tide value",
                zorder=3,
            )
        for _, r in sub.iterrows():
            ax2.text(r["spring_tidal_range_m"] + 0.08, r["D10_m"] + 0.04, r["label"], fontsize=6.9, color="#334155")
    valid = rp[rp["source_status"].eq("source_verified")].dropna(subset=["spring_tidal_range_m", "D10_m"])
    ax2.set_xlabel("Tidal range (m)")
    ax2.set_ylabel(r"$D_{10}$ (m)")
    ax2.set_title("Tidal-regime context", loc="left", fontweight="bold")
    ax2.grid(color="#E2E8F0", lw=0.6)
    handles, labels = ax2.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax2.legend(unique.values(), unique.keys(), frameon=False, loc="upper left", fontsize=6.3)
    ax2.text(
        0.04,
        0.06,
        "Filled markers denote source-verified tidal values",
        transform=ax2.transAxes,
        fontsize=6.8,
        color="#475569",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )
    panel(ax2, "c")

    save(fig, "FigS1_water_level_definition")


def binned_pressure(daily: pd.DataFrame, sid: str, n_bins: int = 26) -> pd.DataFrame:
    sub = daily.loc[daily["station_id"].eq(sid), ["pressure_msl_min", "surge_m"]].dropna().copy()
    sub["bin"] = pd.qcut(sub["pressure_msl_min"], n_bins, duplicates="drop")
    out = sub.groupby("bin", observed=True).agg(
        pressure=("pressure_msl_min", "median"),
        surge=("surge_m", "median"),
        q25=("surge_m", lambda x: x.quantile(0.25)),
        q75=("surge_m", lambda x: x.quantile(0.75)),
        n=("surge_m", "size"),
    )
    out["station_id"] = sid
    return out.reset_index(drop=True)


def make_fig3(corr: pd.DataFrame) -> None:
    gssr = pd.read_parquet(PROCESSED / "gssr_daily_merged.parquet")
    drivers = pd.read_parquet(PROCESSED / "drivers_daily.parquet")
    daily = gssr.merge(drivers, on=["station_id", "date"], how="inner")
    daily.to_parquet(FIG_SOURCE / "Fig3_daily_merged_source.parquet", index=False)

    composite = event_composites(daily, corr)

    fig = plt.figure(figsize=(12.0, 5.1))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.0, 1.08], wspace=0.30)
    axh = fig.add_subplot(gs[0, 0])
    axc = fig.add_subplot(gs[0, 1])
    heat = corr[["pressure", "wind", "precipitation"]].to_numpy()
    im = axh.imshow(heat, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1), aspect="auto")
    axh.set_xticks([0, 1, 2])
    axh.set_xticklabels(["Pressure", "Wind", "Precip."])
    axh.set_yticks(np.arange(len(corr)))
    axh.set_yticklabels(corr["label"])
    axh.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    axh.set_yticks(np.arange(-0.5, len(corr), 1), minor=True)
    axh.grid(which="minor", color="white", lw=1.1)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            val = heat[i, j]
            axh.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7.2, color="white" if abs(val) > 0.55 else "#111827")
    axh.set_title("Daily surge-meteorology rank correlations", loc="left", fontweight="bold")
    cb = fig.colorbar(im, ax=axh, fraction=0.046, pad=0.04)
    cb.set_label("Spearman rho")
    panel(axh, "a")

    draw_event_composite(axc, composite)
    panel(axc, "b")
    fig.subplots_adjust(bottom=0.20)
    save(fig, "FigS2_process_coherence")
    make_fig3_pressure_supplement(corr, daily)


def daily_wind_direction_metrics() -> pd.DataFrame:
    rows = []
    for path in sorted(OPEN_METEO_HOURLY.glob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        station_id = payload.get("meta", {}).get("station_id")
        hourly = payload.get("data", {}).get("hourly", {})
        if not station_id or "wind_direction_10m" not in hourly:
            continue
        df = pd.DataFrame(
            {
                "time": pd.to_datetime(hourly["time"]),
                "wind_speed_10m_kmh": pd.to_numeric(hourly["wind_speed_10m"], errors="coerce"),
                "wind_direction_10m_deg": pd.to_numeric(hourly["wind_direction_10m"], errors="coerce"),
            }
        ).dropna()
        if df.empty:
            continue
        df["station_id"] = station_id
        df["date"] = df["time"].dt.floor("D")
        df["wind_speed_10m_ms"] = df["wind_speed_10m_kmh"] / 3.6
        selected = df.loc[df.groupby("date")["wind_speed_10m_ms"].idxmax()].copy()
        theta = np.deg2rad(selected["wind_direction_10m_deg"].to_numpy(dtype=float))
        # Meteorological wind direction is the direction from which wind blows.
        selected["wind_u_at_max_ms"] = -selected["wind_speed_10m_ms"].to_numpy(dtype=float) * np.sin(theta)
        selected["wind_v_at_max_ms"] = -selected["wind_speed_10m_ms"].to_numpy(dtype=float) * np.cos(theta)
        azimuth = np.deg2rad(ALONGSHORE_AZIMUTH_DEG.get(station_id, 90.0))
        e_east = np.sin(azimuth)
        e_north = np.cos(azimuth)
        selected["alongshore_wind_component_ms"] = selected["wind_u_at_max_ms"] * e_east + selected["wind_v_at_max_ms"] * e_north
        selected["alongshore_wind_stress_proxy_m2s2"] = (
            selected["wind_speed_10m_ms"] * selected["alongshore_wind_component_ms"]
        )
        selected["alongshore_azimuth_deg"] = ALONGSHORE_AZIMUTH_DEG.get(station_id, 90.0)
        rows.append(
            selected[
                [
                    "station_id",
                    "date",
                    "wind_direction_10m_deg",
                    "wind_speed_10m_ms",
                    "wind_u_at_max_ms",
                    "wind_v_at_max_ms",
                    "alongshore_azimuth_deg",
                    "alongshore_wind_component_ms",
                    "alongshore_wind_stress_proxy_m2s2",
                ]
            ].rename(columns={"wind_direction_10m_deg": "wind_direction_at_max_deg"})
        )
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(FIG_SOURCE / "Fig3_daily_wind_direction_metrics.csv", index=False)
    return out


def event_composites(daily: pd.DataFrame, corr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    d = daily.copy()
    d["wind_speed_10m_max_ms"] = d["wind_speed_10m_max"] / 3.6
    wind_dir = daily_wind_direction_metrics()
    if not wind_dir.empty:
        d = d.merge(wind_dir, on=["station_id", "date"], how="left")
    d["year"] = d["date"].dt.year
    d = d[d["year"].between(1980, 2010)].copy()
    climatology = d.groupby("station_id").agg(
        pressure_mean=("pressure_msl_min", "mean"),
        wind_mean=("wind_speed_10m_max_ms", "mean"),
        alongshore_stress_mean=("alongshore_wind_stress_proxy_m2s2", "mean"),
        surge_mean=("surge_m", "mean"),
    )
    roles = corr.set_index("station_id")["coherence_role"].to_dict()
    pressure = corr.set_index("station_id")["pressure"].to_dict()
    for sid, sub in d.groupby("station_id"):
        event_dates = sub.loc[sub.groupby("year")["surge_m"].idxmax(), ["year", "date"]]
        clim = climatology.loc[sid]
        for _, event in event_dates.iterrows():
            for rel in range(-3, 4):
                date = event["date"] + pd.Timedelta(days=rel)
                row = sub[sub["date"].eq(date)]
                if row.empty:
                    continue
                r = row.iloc[0]
                rows.append(
                    {
                        "station_id": sid,
                        "label": SHORT.get(sid, sid),
                        "event_year": int(event["year"]),
                        "relative_day": rel,
                        "surge_m": float(r["surge_m"]),
                        "surge_anomaly_m": float(r["surge_m"] - clim["surge_mean"]),
                        "pressure_anomaly_hpa": float(r["pressure_msl_min"] - clim["pressure_mean"]),
                        "wind_speed_anomaly_ms": float(r["wind_speed_10m_max_ms"] - clim["wind_mean"]),
                        "wind_direction_at_max_deg": float(r["wind_direction_at_max_deg"]) if np.isfinite(r.get("wind_direction_at_max_deg", np.nan)) else np.nan,
                        "alongshore_azimuth_deg": float(r["alongshore_azimuth_deg"]) if np.isfinite(r.get("alongshore_azimuth_deg", np.nan)) else np.nan,
                        "alongshore_wind_stress_proxy_m2s2": float(r["alongshore_wind_stress_proxy_m2s2"])
                        if np.isfinite(r.get("alongshore_wind_stress_proxy_m2s2", np.nan))
                        else np.nan,
                        "alongshore_wind_stress_anomaly_m2s2": float(
                            r["alongshore_wind_stress_proxy_m2s2"] - clim["alongshore_stress_mean"]
                        )
                        if np.isfinite(r.get("alongshore_wind_stress_proxy_m2s2", np.nan))
                        else np.nan,
                        "pressure_rho": float(pressure.get(sid, np.nan)),
                        "event_group": (
                            "pressure-coherent European sites"
                            if roles.get(sid, "").startswith("pressure-coherent")
                            else "weak/regime-dependent daily-local sites"
                        ),
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(FIG_SOURCE / "Fig3_event_composites.csv", index=False)
    return out


def draw_event_composite(ax: plt.Axes, composite: pd.DataFrame) -> None:
    groups = composite.groupby(["event_group", "relative_day"], as_index=False).agg(
        pressure=("pressure_anomaly_hpa", "mean"),
        wind=("wind_speed_anomaly_ms", "mean"),
        surge=("surge_anomaly_m", "mean"),
        n=("surge_m", "size"),
    )
    colors = {
        "pressure-coherent European sites": "#1D4ED8",
        "weak/regime-dependent daily-local sites": "#64748B",
    }
    short_group = {
        "pressure-coherent European sites": "Pressure-coherent sites",
        "weak/regime-dependent daily-local sites": "Other focal sites",
    }
    for group, sub in groups.groupby("event_group"):
        sub = sub.sort_values("relative_day")
        ax.plot(sub["relative_day"], sub["pressure"], marker="o", lw=2.0, color=colors[group], label=f"{short_group[group]}: pressure")
    ax.axvline(0, color="#111827", lw=0.8, ls="--")
    ax.axhline(0, color="#CBD5E1", lw=0.8)
    ax.set_xlabel("Days relative to annual maximum surge")
    ax.set_ylabel("Pressure anomaly (hPa)")
    ax.set_title("Annual-maximum-surge event composite", loc="left", fontweight="bold")
    ax.grid(color="#E2E8F0", lw=0.55)
    ax2 = ax.twinx()
    for group, sub in groups.groupby("event_group"):
        sub = sub.sort_values("relative_day")
        ax2.plot(sub["relative_day"], sub["wind"], marker="s", lw=1.6, ls="--", color=colors[group], alpha=0.80, label=f"{short_group[group]}: wind")
    ax2.set_ylabel("Wind-speed anomaly (m s-1)")
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
        handles1 + handles2,
        labels1 + labels2,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        fontsize=6.3,
        ncol=2,
    )

def make_fig3_pressure_supplement(corr: pd.DataFrame, daily: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(9.8, 4.6))
    gs = GridSpec(1, 2, width_ratios=[1.0, 1.0], wspace=0.28, figure=fig)
    axes = [fig.add_subplot(gs[0, i]) for i in range(2)]
    hb = None
    for ax, sid, title in [
        (axes[0], "newlyn-p001-uk", "Newlyn: pressure-coherent extratropical example"),
        (axes[1], "charleston-sc", "Charleston: weak daily-local example"),
    ]:
        sub = daily[daily["station_id"].eq(sid)]
        hb = ax.hexbin(
            sub["pressure_msl_min"],
            sub["surge_m"],
            gridsize=42,
            cmap="Blues",
            mincnt=1,
            linewidths=0,
            norm=LogNorm(),
        )
        b = binned_pressure(daily, sid)
        b.to_csv(FIG_SOURCE / f"Fig3_{sid}_pressure_bins.csv", index=False)
        ax.plot(b["pressure"], b["surge"], color="#C1121F", lw=2.1, label="binned median")
        ax.fill_between(b["pressure"], b["q25"], b["q75"], color="#F4A6A6", alpha=0.35, lw=0, label="IQR")
        rho = corr.loc[corr["station_id"].eq(sid), "pressure"].iloc[0]
        ax.text(0.05, 0.92, rf"$\rho$ = {rho:.3f}", transform=ax.transAxes, bbox={"boxstyle": "round,pad=0.24", "fc": "white", "ec": "#CBD5E1"})
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Daily minimum mean sea-level pressure (hPa)")
        ax.set_ylabel("GSSR daily surge (m)")
        ax.grid(color="#E2E8F0", lw=0.55)
    if hb is not None:
        cbar = fig.colorbar(hb, ax=axes, fraction=0.025, pad=0.035)
        cbar.set_label("daily records per hexbin")
    axes[0].legend(frameon=False, loc="upper right")
    panel(axes[0], "a")
    panel(axes[1], "b")
    fig.suptitle("Supplementary Figure S3. Example daily pressure-surge diagnostic relationships", y=1.02, fontweight="bold")
    save_supp(fig, "FigS3_pressure_response_examples")


def add_scale_bar(ax: plt.Axes, lon0: float, lat0: float, length_km: float = 2.0) -> None:
    deg = length_km / (111.32 * np.cos(np.deg2rad(lat0)))
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    sx = x0 + 0.08 * (x1 - x0)
    sy = y0 + 0.08 * (y1 - y0)
    ax.plot([sx, sx + deg], [sy, sy], color="#111827", lw=2.4, solid_capstyle="butt")
    ax.text(sx + deg / 2, sy + 0.025 * (y1 - y0), f"{length_km:g} km", ha="center", va="bottom", fontsize=7, color="#111827")


def rgba_overlay(mask: np.ndarray, color: str, alpha: float) -> np.ndarray:
    rgba = np.zeros(mask.shape + (4,), dtype=float)
    rgba[mask, :3] = mpl.colors.to_rgb(color)
    rgba[mask, 3] = alpha
    return rgba


def neutral_terrain_image(elev: np.ndarray, valid: np.ndarray) -> np.ndarray:
    clipped = np.where(valid, np.clip(elev, -2, 10), np.nan)
    fill = float(np.nanmedian(clipped)) if np.isfinite(clipped).any() else 0.0
    shade_input = np.where(valid, clipped, fill)
    lightsource = LightSource(azdeg=315, altdeg=45)
    rgb = lightsource.shade(
        shade_input,
        cmap=NEUTRAL_TERRAIN_CMAP,
        vmin=-2,
        vmax=10,
        vert_exag=1.8,
        blend_mode="soft",
    )
    if rgb.shape[-1] == 3:
        alpha = np.ones(rgb.shape[:2] + (1,), dtype=float)
        rgb = np.concatenate([rgb, alpha], axis=2)
    rgb[~valid] = mpl.colors.to_rgba("#e8f0f5")
    return rgb


def station_plot_context(station_row: pd.Series):
    st, bbox, lon2d, lat2d, elev, valid, coast, source, tiles = station_dem(station_row)
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
    terrain_rgb = neutral_terrain_image(elev, valid)
    return st, bbox, lon2d, lat2d, elev, valid, coast, source, tiles, extent, terrain_rgb


def draw_common_map_elements(
    ax: plt.Axes,
    st: dict,
    lon2d: np.ndarray,
    lat2d: np.ndarray,
    elev: np.ndarray,
    valid: np.ndarray,
    source: str | None = None,
    scale_km: float = 2.0,
) -> None:
    contour = np.where(valid, elev, np.nan)
    if np.isfinite(contour).any():
        ax.contour(lon2d, lat2d, valid.astype(float), levels=[0.5], colors="#56616f", linewidths=0.45, alpha=0.78)
        ax.contour(lon2d, lat2d, contour, levels=[0, 1, 2], colors=["#ffffff", "#a8b5c4", "#3f4f63"], linewidths=[0.4, 0.45, 0.55], alpha=0.72)
    ax.plot(st["lon"], st["lat"], marker="*", ms=8.2, color="#E11D48", mec="white", mew=0.7, zorder=10)
    add_scale_bar(ax, st["lon"], st["lat"], scale_km)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.tick_params(labelsize=6.2)
    if source:
        ax.text(
            0.02,
            0.98,
            source.replace("DeltaDTM:", ""),
            transform=ax.transAxes,
            va="top",
            fontsize=5.9,
            bbox={"boxstyle": "round,pad=0.14", "fc": "white", "ec": "#CBD5E1", "alpha": 0.90},
            zorder=12,
        )


def draw_neutral_site_map(ax: plt.Axes, station_row: pd.Series, terrain_row: pd.Series, letter: str | None = None) -> None:
    st, _, lon2d, lat2d, elev, valid, _, source, _, extent, terrain_rgb = station_plot_context(station_row)
    ax.imshow(terrain_rgb, origin="lower", extent=extent, aspect="equal", interpolation="bilinear")
    scale = 3 if station_row["station_id"] == "brest-france" else 2
    draw_common_map_elements(ax, st, lon2d, lat2d, elev, valid, source=source, scale_km=scale)
    ax.set_title(
        f"{FULL[station_row['station_id']]}\n8n connected +2 m: {terrain_row['connected_2m_lowland_pct']:.1f}%",
        loc="left",
        fontweight="bold",
        fontsize=7.7,
        pad=3,
    )
    if letter:
        panel(ax, letter)


def draw_audit_layer(
    ax: plt.Axes,
    station_row: pd.Series,
    mode: str,
    letter: str | None = None,
    eta: float = 2.0,
    title_prefix: str | None = None,
) -> None:
    st, _, lon2d, lat2d, elev, valid, coast, source, _, extent, terrain_rgb = station_plot_context(station_row)
    layers = flood_connectivity_layers(elev, valid, eta, connectivity=8)
    below = layers["low"] & coast
    connected = layers["connected"] & coast
    unconnected = below & ~connected
    ax.imshow(terrain_rgb, origin="lower", extent=extent, aspect="equal", interpolation="bilinear")
    if mode == "all":
        ax.imshow(rgba_overlay(below, "#475569", 0.66), origin="lower", extent=extent, interpolation="nearest", aspect="equal")
        title = "all cells below +2 m"
    elif mode == "connected":
        depth = np.where(connected, np.maximum(0, eta - elev), np.nan)
        ax.imshow(depth, origin="lower", extent=extent, cmap=FLOOD_CMAP, vmin=0, vmax=eta, alpha=0.92, interpolation="nearest", aspect="equal")
        title = "ocean-connected depth"
    elif mode == "unconnected":
        ax.imshow(rgba_overlay(unconnected, "#D97706", 0.78), origin="lower", extent=extent, interpolation="nearest", aspect="equal")
        title = "unconnected low cells"
    else:
        raise ValueError(f"unknown audit map mode: {mode}")
    ax.imshow(rgba_overlay(layers["seed"], "#0B5CAD", 0.88), origin="lower", extent=extent, interpolation="nearest", aspect="equal")
    draw_common_map_elements(ax, st, lon2d, lat2d, elev, valid, source=None, scale_km=2)
    if mode == "all":
        pct = 100 * below.sum() / coast.sum() if coast.sum() else 0.0
    elif mode == "connected":
        pct = 100 * connected.sum() / coast.sum() if coast.sum() else 0.0
    else:
        pct = 100 * unconnected.sum() / coast.sum() if coast.sum() else 0.0
    prefix = FULL[station_row["station_id"]] if title_prefix is None else title_prefix
    map_title = f"{prefix}\n{title}: {pct:.1f}%" if prefix else f"{title}: {pct:.1f}%"
    ax.set_title(map_title, loc="left", fontweight="bold", fontsize=7.3, pad=3)
    if letter:
        panel(ax, letter)


def draw_fig4_legend(ax: plt.Axes, fig: plt.Figure) -> None:
    ax.axis("off")
    ax.text(0.00, 0.98, "Map key", transform=ax.transAxes, va="top", fontsize=9.2, fontweight="bold")
    dem_sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=-2, vmax=10), cmap=NEUTRAL_TERRAIN_CMAP)
    ax.text(0.02, 0.86, "Neutral DeltaDTM terrain (m)", transform=ax.transAxes, fontsize=6.9, color="#334155")
    cax_dem = ax.inset_axes([0.05, 0.77, 0.82, 0.065])
    cb_dem = fig.colorbar(dem_sm, cax=cax_dem, orientation="horizontal", extend="both")
    cb_dem.ax.tick_params(labelsize=6.1)
    depth_sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=0, vmax=2), cmap=FLOOD_CMAP)
    ax.text(0.02, 0.64, "Connected static water depth (m)", transform=ax.transAxes, fontsize=6.9, color="#334155")
    cax_depth = ax.inset_axes([0.05, 0.55, 0.82, 0.065])
    cb_depth = fig.colorbar(depth_sm, cax=cax_depth, orientation="horizontal")
    cb_depth.ax.tick_params(labelsize=6.1)
    legend_items = [
        ("#475569", "all land cells below +2 m", 0.66),
        ("#0B5CAD", "boundary-linked ocean/water seed", 0.88),
        ("#D97706", "below +2 m but not connected", 0.78),
    ]
    y = 0.41
    for color, label, alpha in legend_items:
        ax.add_patch(Rectangle((0.03, y), 0.065, 0.055, facecolor=color, edgecolor="#334155", alpha=alpha, transform=ax.transAxes))
        ax.text(0.12, y + 0.028, label, transform=ax.transAxes, va="center", fontsize=7.2, color="#334155")
        y -= 0.090
    ax.plot(0.062, y + 0.027, marker="*", ms=7, color="#E11D48", mec="white", mew=0.6, transform=ax.transAxes)
    ax.text(0.12, y + 0.027, "tide-gauge station", transform=ax.transAxes, va="center", fontsize=7.2, color="#334155")
    ax.text(
        0.02,
        0.035,
        "Blue is used only for the connected water-depth layer.\nOrange/grey audit layers separate low terrain from marine access.",
        transform=ax.transAxes,
        fontsize=7.0,
        color="#475569",
        va="bottom",
    )


def draw_fraction_bars(ax: plt.Axes, terrain: pd.DataFrame) -> None:
    order = ["sheerness-p015-uk", "newlyn-p001-uk", "aberdeen-p038-uk", "brest-france", "hoekvanholla-hvh-nl"]
    t = terrain.set_index("station_id").loc[order].reset_index()
    x = np.arange(len(t))
    width = 0.34
    ax.bar(x - width / 2, t["connected_2m_lowland_pct"], width=width, color="#08519C", edgecolor="white", label="connected +2 m")
    ax.bar(x + width / 2, t["bathtub_2m_lowland_pct"], width=width, color="#E5E7EB", edgecolor="#D97706", lw=1.0, label="all below +2 m")
    y = t["connected_2m_lowland_pct"].to_numpy()
    yerr05 = np.vstack(
        [
            y - t["connected_2m_dem_pm05_min_pct"].to_numpy(),
            t["connected_2m_dem_pm05_max_pct"].to_numpy() - y,
        ]
    )
    yerr1 = np.vstack(
        [
            y - t["connected_2m_dem_pm1_min_pct"].to_numpy(),
            t["connected_2m_dem_pm1_max_pct"].to_numpy() - y,
        ]
    )
    ax.errorbar(x - width / 2, y, yerr=yerr1, fmt="none", ecolor="#94A3B8", elinewidth=1.1, capsize=4, label="DEM +/-1 m")
    ax.errorbar(x - width / 2, y, yerr=yerr05, fmt="none", ecolor="#111827", elinewidth=1.4, capsize=3, label="DEM +/-0.5 m")
    ax.set_xticks(x)
    ax.set_xticklabels(t["label"], rotation=0)
    ax.set_ylabel("Coastal-lowland fraction (%)")
    ax.set_title("+2 m connected response and vertical-error envelope", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E2E8F0", lw=0.55)
    ax.set_ylim(0, max(45, float(t["bathtub_2m_lowland_pct"].max()) + 5))
    ax.legend(frameon=False, ncol=2, loc="upper right", fontsize=6.8)
    panel(ax, "c")


def draw_dem_error_ensemble(ax: plt.Axes, terrain: pd.DataFrame) -> None:
    order = terrain.sort_values("connected_2m_lowland_pct", ascending=True)["station_id"].tolist()
    t = terrain.set_index("station_id").loc[order].reset_index()
    y = np.arange(len(t))
    ax.hlines(y, t["connected_2m_dem_pm1_min_pct"], t["connected_2m_dem_pm1_max_pct"], color="#CBD5E1", lw=6.0, label="DEM +/-1 m")
    ax.hlines(y, t["connected_2m_dem_pm05_min_pct"], t["connected_2m_dem_pm05_max_pct"], color="#64748B", lw=2.8, label="DEM +/-0.5 m")
    ax.scatter(t["connected_2m_lowland_pct"], y, s=38, color="#08519C", edgecolor="white", lw=0.7, zorder=3, label="baseline")
    ax.set_yticks(y)
    ax.set_yticklabels(t["label"])
    ax.set_xlabel("+2 m connected lowland fraction (%)")
    ax.set_title("DEM vertical-error ensemble", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#E2E8F0", lw=0.55)
    ax.legend(frameon=False, loc="lower right", fontsize=6.8)


def draw_connectivity_sensitivity(ax: plt.Axes, terrain: pd.DataFrame) -> None:
    order = terrain.sort_values("connected_2m_lowland_pct", ascending=True)["station_id"].tolist()
    t = terrain.set_index("station_id").loc[order].reset_index()
    y = np.arange(len(t))
    ax.hlines(y, t["connected4_2m_lowland_pct"], t["connected_2m_lowland_pct"], color="#CBD5E1", lw=2.0, zorder=1)
    ax.scatter(t["connected_2m_lowland_pct"], y, s=38, color="#08519C", edgecolor="white", lw=0.6, label="8-neighbour", zorder=3)
    ax.scatter(t["connected4_2m_lowland_pct"], y, s=34, color="#D97706", edgecolor="white", lw=0.6, label="4-neighbour", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(t["label"])
    ax.set_xlabel("+2 m connected lowland fraction (%)")
    ax.set_title("Neighbour-rule sensitivity", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#E2E8F0", lw=0.55)
    ax.legend(frameon=False, loc="lower right", fontsize=7.0)


def draw_method_schematic(ax: plt.Axes) -> None:
    ax.axis("off")
    panel(ax, "d")
    ax.text(0.02, 0.88, "Connectivity-screening workflow", transform=ax.transAxes, fontsize=9.5, fontweight="bold", va="top")
    boxes = [
        ("DeltaDTM elevation", "mask nodata\ncoastal-lowland cells"),
        ("Candidate depth", "h=max(0, eta-z)\neta=+0.5,+1,+2 m"),
        ("Boundary ocean seed", "boundary-linked\nwater/no-data only"),
        ("Connectivity filter", "8-neighbour primary\n4-neighbour audit"),
        ("Connected sensitivity", "static depth layer\nlowland fraction"),
    ]
    box_w = 0.162
    x0s = np.linspace(0.03, 0.805, len(boxes))
    for i, ((title, body), x0) in enumerate(zip(boxes, x0s)):
        ax.add_patch(Rectangle((x0, 0.24), box_w, 0.44, facecolor="#F8FAFC", edgecolor="#94A3B8", lw=0.8, transform=ax.transAxes))
        ax.text(x0 + 0.012, 0.60, title, transform=ax.transAxes, fontsize=7.6, fontweight="bold", va="top", color="#1F2937")
        ax.text(x0 + 0.012, 0.46, body, transform=ax.transAxes, fontsize=6.7, va="top", color="#475569", linespacing=1.25)
        if i < len(boxes) - 1:
            ax.annotate(
                "",
                xy=(x0s[i + 1] - 0.012, 0.46),
                xytext=(x0 + box_w + 0.010, 0.46),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.1},
            )
    ax.text(
        0.03,
        0.08,
        "The output is a relative static terrain-sensitivity screen; it does not model defence performance, waves, river flow, drainage, roughness or vertical-datum transformation.",
        transform=ax.transAxes,
        fontsize=7.4,
        color="#475569",
    )


def make_fig4_connectivity_supplement(stations: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(10.8, 14.2))
    gs = GridSpec(len(EU_ORDER), 3, figure=fig, wspace=0.16, hspace=0.42)
    modes = [("all", "All below +2 m"), ("connected", "Ocean-connected +2 m"), ("unconnected", "Unconnected below +2 m")]
    for r, sid in enumerate(EU_ORDER):
        station_row = stations[stations["station_id"].eq(sid)].iloc[0]
        for c, (mode, heading) in enumerate(modes):
            ax = fig.add_subplot(gs[r, c])
            title_prefix = FULL[sid] if c == 0 else ""
            draw_audit_layer(ax, station_row, mode=mode, title_prefix=title_prefix)
            if r < len(EU_ORDER) - 1:
                ax.set_xlabel("")
            if c > 0:
                ax.set_ylabel("")
            if r == 0:
                ax.text(0.5, 1.18, heading, transform=ax.transAxes, ha="center", va="bottom", fontsize=9.0, fontweight="bold")
    fig.suptitle("Supplementary Figure S4. Connectivity audit layers for all five DeltaDTM terrain windows", y=0.995, fontweight="bold")
    fig.text(
        0.5,
        0.010,
        "Grey marks all land cells below +2 m; blue marks boundary-connected static water-depth candidates; orange marks below-level cells excluded from the connected metric.",
        ha="center",
        fontsize=8.0,
        color="#475569",
    )
    save_supp(fig, "FigS4_connectivity_audit")


def make_fig4(stations: pd.DataFrame, terrain: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(11.2, 13.6))
    gs = GridSpec(4, 2, figure=fig, height_ratios=[1.03, 1.03, 0.85, 0.42], wspace=0.20, hspace=0.38)

    terrain_i = terrain.set_index("station_id")
    representative = [
        ("sheerness-p015-uk", "Sheerness: high connected-lowland response"),
        ("hoekvanholla-hvh-nl", "Hoek van Holland: window/seed-sensitive protected lowland"),
    ]
    for c, (sid, title) in enumerate(representative):
        station_row = stations[stations["station_id"].eq(sid)].iloc[0]
        row = terrain_i.loc[sid]
        ax = fig.add_subplot(gs[0, c])
        draw_audit_layer(ax, station_row, mode="connected", letter="a" if c == 0 else None)
        ax.set_title(
            f"{title}\nconnected +2 m: {row['connected_2m_lowland_pct']:.1f}% | all below +2 m: {row['bathtub_2m_lowland_pct']:.1f}%",
            loc="left",
            fontweight="bold",
            fontsize=7.7,
            pad=3,
        )

    audit = [
        ("sheerness-p015-uk", "Sheerness unconnected low cells"),
        ("hoekvanholla-hvh-nl", "Hoek van Holland unconnected low cells"),
    ]
    for c, (sid, title) in enumerate(audit):
        station_row = stations[stations["station_id"].eq(sid)].iloc[0]
        ax = fig.add_subplot(gs[1, c])
        draw_audit_layer(ax, station_row, mode="unconnected", letter="b" if c == 0 else None, title_prefix=title)

    ax_bar = fig.add_subplot(gs[2, 0])
    draw_fraction_bars(ax_bar, terrain)
    ax_sens = fig.add_subplot(gs[2, 1])
    draw_dem_error_ensemble(ax_sens, terrain)

    ax_method = fig.add_subplot(gs[3, :])
    draw_method_schematic(ax_method)

    fig.suptitle("Figure 3. DeltaDTM connected-lowland sensitivity and connectivity audit", y=0.996, fontweight="bold")
    fig.text(
        0.5,
        0.008,
        "Neutral terrain removes the earlier colour ambiguity: blue is reserved for connected static water depth, while grey/orange audit layers show below-level cells before and after connectivity filtering.",
        ha="center",
        fontsize=8.0,
        color="#475569",
    )
    save(fig, "Fig4_deltadtm_terrain_sensitivity")
    make_fig4_connectivity_supplement(stations)


def make_fig5(rp: pd.DataFrame, corr: pd.DataFrame, terrain: pd.DataFrame, stations: pd.DataFrame) -> None:
    extended_path = FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv"
    if extended_path.exists():
        make_fig5_extended()
        return

    merged = terrain.merge(rp[["station_id", "D10_m", "coast_rp_rp10_m"]], on="station_id").merge(
        corr[["station_id", "pressure"]], on="station_id"
    )
    merged["coast_rp_rank"] = merged["coast_rp_rp10_m"].rank(ascending=False, method="min").astype(int)
    merged["terrain_rank"] = merged["connected_2m_lowland_pct"].rank(ascending=False, method="min").astype(int)
    merged["D10_rank"] = merged["D10_m"].rank(ascending=False, method="min").astype(int)
    merged["rank_mismatch_terrain_minus_coast"] = merged["terrain_rank"] - merged["coast_rp_rank"]
    merged["terrain_class"] = np.select(
        [
            merged["connected_2m_lowland_pct"].ge(20),
            merged["connected_2m_lowland_pct"].lt(10),
        ],
        ["high connected sensitivity", "low connected sensitivity"],
        default="intermediate connected sensitivity",
    )
    merged["D10_class"] = np.select(
        [
            merged["D10_m"].ge(3.0),
            merged["D10_m"].lt(1.0),
        ],
        ["high product-definition divergence", "low product-definition divergence"],
        default="moderate product-definition divergence",
    )
    merged["pressure_class"] = np.where(merged["pressure"].le(-0.5), "pressure-coherent daily surge", "weak/regime-dependent pressure screen")
    merged["class"] = np.select(
        [
            merged["connected_2m_lowland_pct"].ge(20),
            (merged["bathtub_2m_lowland_pct"] - merged["connected_2m_lowland_pct"]).ge(20),
            merged["connected_2m_lowland_pct"].lt(10),
        ],
        [
            "high connected-lowland response",
            "window/seed-sensitive protected lowland",
            "water-level high / connected-terrain low",
        ],
        default="intermediate process-terrain response",
    )
    merged[
        [
            "station_id",
            "label",
            "D10_m",
            "D10_rank",
            "coast_rp_rp10_m",
            "coast_rp_rank",
            "pressure",
            "connected_2m_lowland_pct",
            "terrain_rank",
            "rank_mismatch_terrain_minus_coast",
            "connected_1m_lowland_pct",
            "connected_0.5m_lowland_pct",
            "bathtub_2m_lowland_pct",
            "median_lowland_elev_m",
            "D10_class",
            "terrain_class",
            "pressure_class",
            "class",
        ]
    ].to_csv(FIG_SOURCE / "Fig5_process_terrain_typology.csv", index=False)
    rho_coast = stats.spearmanr(merged["coast_rp_rp10_m"], merged["connected_2m_lowland_pct"]).statistic
    tau_coast = stats.kendalltau(merged["coast_rp_rp10_m"], merged["connected_2m_lowland_pct"]).statistic
    rho_d10 = stats.spearmanr(merged["D10_m"], merged["connected_2m_lowland_pct"]).statistic
    top_n = max(1, int(np.ceil(0.4 * len(merged))))
    top_water = set(merged.nsmallest(top_n, "coast_rp_rank")["station_id"])
    top_terrain = set(merged.nsmallest(top_n, "terrain_rank")["station_id"])
    mismatch_fraction = 1.0 - len(top_water & top_terrain) / top_n
    pd.DataFrame(
        [
            {
                "n_terrain_sites": len(merged),
                "top_fraction_used": 0.4,
                "top_n": top_n,
                "top_water_sites": ";".join(sorted(top_water)),
                "top_terrain_sites": ";".join(sorted(top_terrain)),
                "top_rank_mismatch_fraction": mismatch_fraction,
                "spearman_coastrp_vs_connected_2m": rho_coast,
                "kendall_coastrp_vs_connected_2m": tau_coast,
                "spearman_D10_vs_connected_2m": rho_d10,
            }
        ]
    ).to_csv(FIG_SOURCE / "Fig5_rank_mismatch_diagnostics.csv", index=False)

    fig = plt.figure(figsize=(12.2, 7.35))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1.05, 1.0], height_ratios=[1, 0.92], wspace=0.28, hspace=0.35)
    ax_hyp = fig.add_subplot(gs[0, 0])
    ax_resp = fig.add_subplot(gs[1, 0])
    ax_rank = fig.add_subplot(gs[:, 1])

    colors = {
        "Sheerness": "#D1495B",
        "Hoek v.H.": "#0E7C7B",
        "Newlyn": "#F59E0B",
        "Brest": "#7C3AED",
        "Aberdeen": "#64748B",
    }
    hyps = []
    for sid in EU_TERRAIN_IDS:
        st = stations[stations["station_id"].eq(sid)].iloc[0]
        _, _, _, _, elev, valid, coast, _, _ = station_dem(st)
        vals = elev[coast]
        vals = vals[np.isfinite(vals)]
        vals = vals[(vals > -5) & (vals <= 15)]
        xs = np.linspace(-1, 12, 180)
        ys = np.array([(vals <= x).mean() for x in xs]) * 100
        label = SHORT[sid]
        hyps.extend({"station_id": sid, "elevation_m": x, "cum_lowland_pct": y} for x, y in zip(xs, ys))
        ax_hyp.plot(xs, ys, lw=2.0, color=colors[label], label=label)
    pd.DataFrame(hyps).to_csv(FIG_SOURCE / "Fig4_hypsometry_curves.csv", index=False)
    for eta, alpha in [(0.5, 0.25), (1.0, 0.32), (2.0, 0.40)]:
        ax_hyp.axvline(eta, color="#111827", ls="--", lw=0.8, alpha=alpha + 0.25)
        ax_hyp.text(eta + 0.05, 96, f"+{eta:g} m", rotation=90, va="top", fontsize=7.0, color="#334155")
    ax_hyp.set_xlim(-1, 12)
    ax_hyp.set_ylim(0, 100)
    ax_hyp.set_xlabel("DeltaDTM elevation within coastal-lowland mask (m)")
    ax_hyp.set_ylabel("Cumulative lowland fraction (%)")
    ax_hyp.set_title("Lowland hypsometry controls terrain response", loc="left", fontweight="bold")
    ax_hyp.grid(color="#E2E8F0", lw=0.55)
    ax_hyp.legend(frameon=False, ncol=2, loc="lower right")
    panel(ax_hyp, "a")

    order = ["sheerness-p015-uk", "hoekvanholla-hvh-nl", "newlyn-p001-uk", "brest-france", "aberdeen-p038-uk"]
    t = merged.set_index("station_id").loc[order].reset_index()
    t = t.sort_values("connected_2m_lowland_pct", ascending=False).reset_index(drop=True)
    x = np.arange(len(t))
    width = 0.34
    ax_resp.bar(x - width / 2, t["connected_2m_lowland_pct"], width=width, color="#174EA6", edgecolor="white", label="connected +2 m")
    ax_resp.bar(x + width / 2, t["bathtub_2m_lowland_pct"], width=width, color="#E5E7EB", edgecolor="#D1495B", lw=1.1, label="all below +2 m")
    ax_resp.set_xticks(x)
    ax_resp.set_xticklabels(t["label"])
    ax_resp.set_ylim(0, max(45, t["bathtub_2m_lowland_pct"].max() + 4))
    ax_resp.set_ylabel("Lowland fraction (%)")
    ax_resp.set_title("Connectivity filtering separates low terrain from marine access", loc="left", fontweight="bold")
    ax_resp.grid(axis="y", color="#E2E8F0", lw=0.55)
    ax_resp.legend(frameon=False, ncol=1, loc="upper right", fontsize=7.0)
    panel(ax_resp, "b")

    rank_order = merged.sort_values("coast_rp_rank")
    cmap = {"positive": "#D1495B", "negative": "#0E7C7B", "zero": "#64748B"}
    for _, r in rank_order.iterrows():
        mismatch = int(r["rank_mismatch_terrain_minus_coast"])
        color = cmap["zero"] if mismatch == 0 else cmap["positive"] if mismatch > 0 else cmap["negative"]
        ax_rank.plot([0, 1], [r["coast_rp_rank"], r["terrain_rank"]], color=color, lw=2.2, alpha=0.9)
        ax_rank.scatter([0, 1], [r["coast_rp_rank"], r["terrain_rank"]], color=color, s=42, edgecolor="white", lw=0.8, zorder=3)
        ax_rank.text(-0.04, r["coast_rp_rank"], r["label"], ha="right", va="center", fontsize=7.8)
        ax_rank.text(1.04, r["terrain_rank"], r["label"], ha="left", va="center", fontsize=7.8)
    ax_rank.set_xlim(-0.22, 1.22)
    ax_rank.set_ylim(len(merged) + 0.55, 0.45)
    ax_rank.set_xticks([0, 1])
    ax_rank.set_xticklabels(["COAST-RP RP10\npriority rank", "+2 m connected\nterrain rank"])
    ax_rank.set_yticks(np.arange(1, len(merged) + 1))
    ax_rank.set_ylabel("Rank (1 = highest)")
    ax_rank.set_title("Rank mismatch in screening priority", loc="left", fontweight="bold")
    ax_rank.grid(axis="y", color="#E2E8F0", lw=0.55)
    ax_rank.text(
        0.50,
        0.07,
        f"Spearman rho = {rho_coast:.2f}; Kendall tau = {tau_coast:.2f}\nTop-40% mismatch = {mismatch_fraction:.0%}",
        transform=ax_rank.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.0,
        color="#334155",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )
    panel(ax_rank, "c")

    fig.suptitle("Terrain response and rank mismatch in process-terrain screening", y=1.01, fontweight="bold")
    save(fig, "Fig5_process_terrain_typology")


def make_fig5_extended() -> None:
    ext = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv")
    diag = pd.read_csv(FIG_SOURCE / "Fig5_nw_europe_rank_mismatch_diagnostics.csv").iloc[0]
    pool_summary_path = FIG_SOURCE / "Fig5_candidate_pool_threshold_sensitivity.csv"
    pool_summary = pd.read_csv(pool_summary_path) if pool_summary_path.exists() else pd.DataFrame()
    ext = ext.dropna(subset=["coast_rp_rp10_m", "connected_2m_lowland_pct", "coast_rp_rank", "terrain_rank"]).copy()
    ext["coast_rp_rank"] = ext["coast_rp_rank"].astype(int)
    ext["terrain_rank"] = ext["terrain_rank"].astype(int)
    top_n = int(diag["top_n"])
    ext["priority_class"] = "other stations"
    water_top = ext["coast_rp_rank"].le(top_n)
    terrain_top = ext["terrain_rank"].le(top_n)
    ext.loc[water_top & terrain_top, "priority_class"] = "top in both"
    ext.loc[water_top & ~terrain_top, "priority_class"] = "water-level top only"
    ext.loc[~water_top & terrain_top, "priority_class"] = "terrain top only"
    ext.to_csv(FIG_SOURCE / "Fig5_process_terrain_typology.csv", index=False)

    fig = plt.figure(figsize=(12.4, 7.4))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1.08, 1.0], height_ratios=[1, 1], wspace=0.30, hspace=0.38)
    ax_scatter = fig.add_subplot(gs[0, 0])
    ax_sets = fig.add_subplot(gs[1, 0])
    ax_rank = fig.add_subplot(gs[:, 1])

    sc = ax_scatter.scatter(
        ext["coast_rp_rp10_m"],
        ext["connected_2m_lowland_pct"],
        c=ext["D10_m"],
        s=42 + 2.2 * ext["gssr_years"],
        cmap="viridis",
        edgecolor="white",
        lw=0.8,
        alpha=0.92,
    )
    label_ids = set(
        ext.nsmallest(top_n, "coast_rp_rank")["station_id"].tolist()
        + ext.nsmallest(top_n, "terrain_rank")["station_id"].tolist()
    )
    for _, r in ext[ext["station_id"].isin(label_ids)].iterrows():
        ax_scatter.text(
            r["coast_rp_rp10_m"] + 0.03,
            r["connected_2m_lowland_pct"] + 0.55,
            SHORT.get(r["station_id"], str(r["station"]).replace(" Van ", " v. ")[:14]),
            fontsize=6.7,
            color="#334155",
        )
    ax_scatter.set_xlabel("COAST-RP RP10 storm tide (m)")
    ax_scatter.set_ylabel("+2 m connected lowland fraction (%)")
    ax_scatter.set_title("Water-level magnitude does not rank connected terrain response", loc="left", fontweight="bold")
    ax_scatter.grid(color="#E2E8F0", lw=0.55)
    cb = fig.colorbar(sc, ax=ax_scatter, fraction=0.046, pad=0.03)
    cb.set_label(r"$D_{10}$ (m)")
    if not pool_summary.empty:
        pool_rows = pool_summary[pool_summary["diagnostic"].eq("candidate-pool threshold sensitivity")].copy()
        pool_rows = pool_rows.sort_values("corr_threshold")
        lines = ["Eligible-pool check"]
        for _, row in pool_rows.iterrows():
            lines.append(
                f"r>={float(row['corr_threshold']):.2f}: n={int(row['n_sites'])}, "
                f"rho={float(row['spearman']):.2f}, overlap={int(row['top_overlap'])}/{int(row['top_n'])}"
            )
        ax_scatter.text(
            0.04,
            0.96,
            "\n".join(lines),
            transform=ax_scatter.transAxes,
            va="top",
            fontsize=7.1,
            color="#334155",
            bbox={"boxstyle": "round,pad=0.32", "facecolor": "white", "edgecolor": "#CBD5E1", "alpha": 0.94},
        )
    panel(ax_scatter, "a")

    top_water = ext.nsmallest(top_n, "coast_rp_rank").sort_values("coast_rp_rank")
    top_terrain = ext.nsmallest(top_n, "terrain_rank").sort_values("terrain_rank")
    ax_sets.axis("off")
    panel(ax_sets, "b")
    ax_sets.text(0.00, 0.98, f"Top {top_n} screening-priority sets", transform=ax_sets.transAxes, va="top", fontweight="bold", fontsize=9.2)
    ax_sets.text(0.02, 0.83, "COAST-RP RP10 top set", transform=ax_sets.transAxes, fontweight="bold", color="#D1495B")
    ax_sets.text(0.56, 0.83, "Connected-terrain top set", transform=ax_sets.transAxes, fontweight="bold", color="#0E7C7B")
    overlap = set(top_water["station_id"]) & set(top_terrain["station_id"])
    for i, (_, r) in enumerate(top_water.iterrows()):
        color = "#64748B" if r["station_id"] in overlap else "#D1495B"
        ax_sets.text(0.03, 0.72 - i * 0.095, f"{int(r['coast_rp_rank'])}. {r['station']}", transform=ax_sets.transAxes, fontsize=7.5, color=color)
    for i, (_, r) in enumerate(top_terrain.iterrows()):
        color = "#64748B" if r["station_id"] in overlap else "#0E7C7B"
        ax_sets.text(0.57, 0.72 - i * 0.095, f"{int(r['terrain_rank'])}. {r['station']}", transform=ax_sets.transAxes, fontsize=7.5, color=color)
    ax_sets.text(
        0.02,
        0.04,
        f"Overlap: {len(overlap)}/{top_n}; top-20% mismatch = {diag['top_rank_mismatch_fraction']:.0%}",
        transform=ax_sets.transAxes,
        fontsize=8.2,
        color="#334155",
        bbox={"boxstyle": "round,pad=0.30", "facecolor": "#F8FAFC", "edgecolor": "#CBD5E1"},
    )

    class_colors = {
        "top in both": "#64748B",
        "water-level top only": "#D1495B",
        "terrain top only": "#0E7C7B",
        "other stations": "#CBD5E1",
    }
    for cls, sub in ext.groupby("priority_class"):
        ax_rank.scatter(
            sub["coast_rp_rank"],
            sub["terrain_rank"],
            s=50 if cls != "other stations" else 28,
            color=class_colors[cls],
            edgecolor="white",
            lw=0.6,
            label=cls,
            alpha=0.95,
            zorder=3 if cls != "other stations" else 2,
        )
    lim = max(int(ext["coast_rp_rank"].max()), int(ext["terrain_rank"].max())) + 1
    ax_rank.plot([1, lim], [1, lim], color="#94A3B8", ls="--", lw=1.0, zorder=1)
    for _, r in ext[ext["priority_class"].ne("other stations")].iterrows():
        ax_rank.text(r["coast_rp_rank"] + 0.25, r["terrain_rank"] + 0.25, str(r["station"])[:13], fontsize=6.5, color="#334155")
    ax_rank.set_xlim(0.3, lim)
    ax_rank.set_ylim(lim, 0.3)
    ax_rank.set_xlabel("COAST-RP RP10 rank (1 = highest)")
    ax_rank.set_ylabel("+2 m connected-terrain rank (1 = highest)")
    ax_rank.set_title("Rank discordance across the 30-station subset", loc="left", fontweight="bold")
    ax_rank.grid(color="#E2E8F0", lw=0.55)
    ax_rank.legend(frameon=False, loc="lower right", fontsize=7.0)
    ax_rank.text(
        0.05,
        0.05,
        f"n={int(diag['n_sites'])}; raw Spearman rho={diag['spearman_coastrp_vs_connected_2m']:.2f}\n"
        f"raw Kendall tau={diag['kendall_coastrp_vs_connected_2m']:.2f}; top-20% mismatch={diag['top_rank_mismatch_fraction']:.0%}",
        transform=ax_rank.transAxes,
        fontsize=8.0,
        color="#334155",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )
    panel(ax_rank, "c")

    fig.suptitle("Figure 4. Storm-tide magnitude and connected terrain response rank NW Europe sites differently", y=1.01, fontweight="bold")
    save(fig, "Fig5_process_terrain_typology")


def build_tables(rp: pd.DataFrame, corr: pd.DataFrame, terrain: pd.DataFrame) -> None:
    rp[
        [
            "full_label",
            "spring_tidal_range_m",
            "gssr_rp10_m",
            "gssr_rp10_bootstrap_p025_m",
            "gssr_rp10_bootstrap_p975_m",
            "coast_rp_rp10_m",
            "nearest3_range_m",
            "within5km_min_rp10_m",
            "within5km_max_rp10_m",
            "rp10_bias_m",
            "D10_m",
            "match_dist_km",
        ]
    ].rename(
        columns={
            "full_label": "Station",
            "spring_tidal_range_m": "Indicative spring tidal range (m)",
            "gssr_rp10_m": "GSSR RP10 surge (m)",
            "gssr_rp10_bootstrap_p025_m": "GSSR RP10 bootstrap 2.5% (m)",
            "gssr_rp10_bootstrap_p975_m": "GSSR RP10 bootstrap 97.5% (m)",
            "coast_rp_rp10_m": "COAST-RP RP10 storm tide (m)",
            "nearest3_range_m": "COAST-RP nearest-3 RP10 range (m)",
            "within5km_min_rp10_m": "COAST-RP within-5km RP10 min (m)",
            "within5km_max_rp10_m": "COAST-RP within-5km RP10 max (m)",
            "rp10_bias_m": "GSSR minus COAST-RP (m)",
            "D10_m": "Storm-tide minus surge (m)",
            "match_dist_km": "Match distance (km)",
        }
    ).to_csv(FIG_SOURCE / "Table2_water_level_indicators.csv", index=False)
    corr[["label", "n_days", "pressure", "wind", "precipitation", "coherence_role"]].rename(
        columns={
            "label": "Station",
            "pressure": "Surge vs pressure",
            "wind": "Surge vs wind",
            "precipitation": "Surge vs precipitation",
            "coherence_role": "Process-coherence role",
        }
    ).to_csv(FIG_SOURCE / "Table3_driver_correlations.csv", index=False)
    table4_columns = [
        "station_id",
        "label",
        "full_label",
        "dem_source",
        "tiles",
        "valid_fraction",
        "median_lowland_elev_m",
        "connected_0.5m_lowland_pct",
        "connected_1m_lowland_pct",
        "connected_2m_lowland_pct",
        "connected4_2m_lowland_pct",
        "connected_2m_dem_pm05_min_pct",
        "connected_2m_dem_pm05_max_pct",
        "connected_2m_dem_pm1_min_pct",
        "connected_2m_dem_pm1_max_pct",
        "bathtub_2m_lowland_pct",
        "unconnected_2m_lowland_pct",
    ]
    terrain[table4_columns].rename(
        columns={
            "label": "Station",
            "dem_source": "DEM source",
            "median_lowland_elev_m": "Median coastal-lowland elevation (m)",
            "connected_0.5m_lowland_pct": "Ocean-connected +0.5 m, 8n (%)",
            "connected_1m_lowland_pct": "Ocean-connected +1.0 m, 8n (%)",
            "connected_2m_lowland_pct": "Ocean-connected +2.0 m, 8n (%)",
            "connected4_2m_lowland_pct": "Ocean-connected +2.0 m, 4n (%)",
            "connected_2m_dem_pm05_min_pct": "DEM +/-0.5 m min connected +2.0 m (%)",
            "connected_2m_dem_pm05_max_pct": "DEM +/-0.5 m max connected +2.0 m (%)",
            "connected_2m_dem_pm1_min_pct": "DEM +/-1.0 m min connected +2.0 m (%)",
            "connected_2m_dem_pm1_max_pct": "DEM +/-1.0 m max connected +2.0 m (%)",
            "bathtub_2m_lowland_pct": "All below +2.0 m (%)",
            "unconnected_2m_lowland_pct": "Unconnected below +2.0 m (%)",
        }
    ).to_csv(FIG_SOURCE / "Table4_deltadtm_connected_sensitivity.csv", index=False)


def main() -> int:
    style()
    ensure_dirs()
    stations = stations_df()
    rp = rp_df(stations)
    corr = corr_df()
    terrain = connected_terrain_df(stations)
    make_fig1(stations)
    make_fig2(rp)
    make_fig3(corr)
    make_fig4(stations, terrain)
    make_fig5(rp, corr, terrain, stations)
    build_tables(rp, corr, terrain)
    print("Refined Fig.2-Fig.5 written to", FIG_MAIN)
    print("Connected terrain source data written to", FIG_SOURCE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create regional agreement, site-contrast and gallery figures for submission."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from add_advanced_terrain_rank_diagnostics import (  # noqa: E402
    LEVELS_M,
    LOWLAND_MAX_M,
    cell_area_km2,
    fixed_km_bbox,
    read_dem_window_fast,
    sum_area,
)
from add_mask_aware_terrain_diagnostics import (  # noqa: E402
    mask_aware_layers,
    resolve_marine_seed,
)
from inundation_sensitivity import valid_mask  # noqa: E402
from publication_style import apply_publication_style  # noqa: E402


FIG_SOURCE = ROOT / "data" / "figure_source"
FIG_MAIN = ROOT / "figures" / "main"


COLORS = {
    "other": "#F8FAFC",
    "coastal": "#D6D3D1",
    "unconnected": "#F59E0B",
    "connected": "#0EA5E9",
    "water": "#8FC6E8",
    "capped": "#6B7280",
}

ARCHETYPE_LABELS = {
    "aligned high storm-tide / high connected-terrain": "High water / high terrain response",
    "high storm-tide / lower connected-terrain": "High water / lower terrain response",
    "lower storm-tide / high connected-terrain": "Lower water / higher fraction response",
}

ARCHETYPE_COLORS = ["#0EA5E9", "#EF4444", "#16A34A"]


def style() -> None:
    apply_publication_style()


def scale_bar(ax: plt.Axes, lon: float, lat: float, km: float = 2.0) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    pad_x = (x1 - x0) * 0.08
    pad_y = (y1 - y0) * 0.08
    lon_len = km / (111.320 * max(math.cos(math.radians(lat)), 0.15))
    xs = [x0 + pad_x, x0 + pad_x + lon_len]
    y = y0 + pad_y
    ax.plot(xs, [y, y], color="#111827", lw=2.2, solid_capstyle="butt")
    ax.text(np.mean(xs), y + (y1 - y0) * 0.025, f"{km:g} km", ha="center", va="bottom", fontsize=7.0)


def emphasize_connected_footprint(
    ax: plt.Axes,
    cls: np.ndarray,
    bbox: tuple[float, float, float, float],
    connected_pct: float,
) -> None:
    """Outline the classified connected cells without changing their extent."""
    connected = cls == 3
    if not connected.any():
        return
    ax.contour(
        connected.astype(float),
        levels=[0.5],
        colors=["#075985"],
        linewidths=0.65,
        origin="upper",
        extent=[bbox[0], bbox[2], bbox[1], bbox[3]],
        zorder=3,
    )
    if connected_pct >= 2.0:
        return
    rows, cols = np.where(connected)
    lon = bbox[0] + (float(np.median(cols)) + 0.5) / cls.shape[1] * (bbox[2] - bbox[0])
    lat = bbox[3] - (float(np.median(rows)) + 0.5) / cls.shape[0] * (bbox[3] - bbox[1])
    ax.annotate(
        f"{connected_pct:.1f}% connected footprint",
        xy=(lon, lat),
        xytext=(0.04, 0.91),
        textcoords="axes fraction",
        ha="left",
        va="top",
        fontsize=7.2,
        color="#075985",
        arrowprops={"arrowstyle": "->", "color": "#075985", "lw": 0.8},
        bbox={"boxstyle": "square,pad=0.18", "facecolor": "white", "edgecolor": "#94A3B8", "alpha": 0.92},
        zorder=5,
    )


def classification_for_station(row: pd.Series) -> tuple[np.ndarray, tuple[float, float, float, float], dict[str, float]]:
    bbox = fixed_km_bbox(float(row["lon"]), float(row["lat"]), 10.0)
    lon2d, lat2d, elev, _, dem_meta, _ = read_dem_window_fast(bbox)
    valid = valid_mask(elev)
    mask, tidal_water, _ = resolve_marine_seed(
        float(row["lon"]),
        float(row["lat"]),
        bbox,
        elev.shape,
        dem_meta["transform"],
        dem_meta["crs"],
    )
    area = cell_area_km2(lon2d, lat2d)
    lowland = valid & (mask == 0) & np.isfinite(elev) & (elev <= LOWLAND_MAX_M)
    layers = mask_aware_layers(elev, valid, mask, 2.0, tidal_water=tidal_water)
    connected = layers["connected"] & lowland
    below = layers["low"] & lowland
    unconnected = below & ~connected
    water = layers["tidal_water"]
    capped = mask == 255
    cls = np.zeros(elev.shape, dtype=np.uint8)
    cls[lowland & ~below] = 1
    cls[unconnected] = 2
    cls[connected] = 3
    cls[water] = 4
    cls[capped] = 5
    denom = sum_area(area, lowland)
    stats = {
        "connected_pct": 100 * sum_area(area, connected) / denom if denom else np.nan,
        "connected_area": sum_area(area, connected),
        "below_area": sum_area(area, below),
        "lowland_area": denom,
    }
    return cls, bbox, stats


def station_threshold_curve(row: pd.Series) -> pd.DataFrame:
    bbox = fixed_km_bbox(float(row["lon"]), float(row["lat"]), 10.0)
    lon2d, lat2d, elev, _, dem_meta, _ = read_dem_window_fast(bbox)
    valid = valid_mask(elev)
    mask, tidal_water, _ = resolve_marine_seed(
        float(row["lon"]),
        float(row["lat"]),
        bbox,
        elev.shape,
        dem_meta["transform"],
        dem_meta["crs"],
    )
    area = cell_area_km2(lon2d, lat2d)
    lowland = valid & (mask == 0) & np.isfinite(elev) & (elev <= LOWLAND_MAX_M)
    denom = sum_area(area, lowland)
    rows = []
    for level in LEVELS_M:
        values = {}
        for shift, label in [(0.0, "baseline"), (-0.5, "lower_dem"), (0.5, "higher_dem")]:
            layers = mask_aware_layers(elev + shift, valid, mask, level, tidal_water=tidal_water)
            conn = layers["connected"] & lowland
            values[label] = 100 * sum_area(area, conn) / denom if denom else np.nan
        rows.append(
            {
                "station_id": row["station_id"],
                "station": row["station"],
                "level_m": level,
                "baseline_pct": values["baseline"],
                "pm05_min_pct": min(values["lower_dem"], values["higher_dem"]),
                "pm05_max_pct": max(values["lower_dem"], values["higher_dem"]),
            }
        )
    return pd.DataFrame(rows)


def short_station_name(name: str) -> str:
    out = str(name)
    for token in [
        " P060 Uk",
        " P063 Uk",
        " P057 Uk",
        " P024 Uk",
        " P015 Uk",
        " P001 Uk",
        " P038 Uk",
        " Del Nl",
        " Hel Nl",
        " Hvh Nl",
    ]:
        out = out.replace(token, "")
    replacements = {
        "Denhelder": "Den Helder",
        "Hoekvanholla": "Hoek van Holland",
        "Dunkerque France": "Dunkerque",
        "Boulogne Sur Mer": "Boulogne-sur-Mer",
    }
    out = out.replace(" Germany", "").strip()
    return replacements.get(out, out)


def draw_evidence_card(ax: plt.Axes, row: pd.Series, n_rank: int, area_max: float, color: str, panel: str) -> None:
    ax.set_axis_off()
    label = ARCHETYPE_LABELS.get(str(row["archetype"]), str(row["archetype"]))
    ax.text(0.0, 0.98, f"{panel}. Indicator values and ranks", transform=ax.transAxes, ha="left", va="top", fontweight="bold")
    ax.text(0.0, 0.82, label, transform=ax.transAxes, ha="left", va="top", fontsize=9.0, color=color, fontweight="bold")
    ax.text(
        0.0,
        0.68,
        "Rank 1 = highest screening priority",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.2,
        color="#475569",
    )
    metrics = [
        ("COAST-RP RP10", float(row["coast_rp_rp10_m"]), 9.0, "m", "#075985"),
        ("Connected fraction", float(row["connected_2m_lowland_pct"]), 100.0, "%", "#0EA5E9"),
        ("Connected area", float(row["connected_2m_area_km2"]), max(area_max, 1.0), "km2", "#16A34A"),
    ]
    y0 = 0.48
    for i, (name, value, max_value, unit, bar_color) in enumerate(metrics):
        y = y0 - i * 0.17
        ax.text(0.0, y + 0.045, name, transform=ax.transAxes, ha="left", va="center", fontsize=7.4, color="#111827")
        ax.add_patch(plt.Rectangle((0.40, y + 0.02), 0.43, 0.055, transform=ax.transAxes, facecolor="#E5E7EB", edgecolor="none"))
        ax.add_patch(
            plt.Rectangle(
                (0.40, y + 0.02),
                0.43 * min(max(value / max_value, 0), 1),
                0.055,
                transform=ax.transAxes,
                facecolor=bar_color,
                edgecolor="none",
                alpha=0.88,
            )
        )
        if unit == "%":
            value_text = f"{value:.1f}%"
        elif unit == "km2":
            value_text = rf"{value:.2f} km$^2$"
        else:
            value_text = f"{value:.2f} m"
        ax.text(0.86, y + 0.047, value_text, transform=ax.transAxes, ha="left", va="center", fontsize=7.4, color="#111827")
    ax.text(
        0.0,
        0.02,
        f"Water rank: {int(row['water_rank'])}/{n_rank}    Connected-fraction rank: {int(row['terrain_rank'])}/{n_rank}",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.0,
        fontweight="bold",
        color="#111827",
    )


def draw_single_threshold_panel(ax: plt.Axes, row: pd.Series, color: str, panel: str) -> None:
    sub = station_threshold_curve(row)
    ax.fill_between(sub["level_m"], sub["pm05_min_pct"], sub["pm05_max_pct"], color=color, alpha=0.15, lw=0)
    ax.plot(sub["level_m"], sub["baseline_pct"], color=color, lw=2.1)
    ax.axvline(2.0, color="#475569", lw=0.9, ls="--")
    ax.scatter([2.0], [float(row["connected_2m_lowland_pct"])], color="#111827", s=18, zorder=4)
    ax.set_ylim(-3, 103)
    ax.set_xlim(0, 3)
    ax.set_xticks([0, 1, 2, 3])
    ax.grid(color="#E2E8F0", lw=0.6)
    ax.set_title(f"{panel}. Threshold response", loc="left", fontweight="bold")
    ax.set_xlabel("Terrain threshold (m)")
    ax.set_ylabel("Connected lowland (%)")
    ax.text(
        0.98,
        0.08,
        "+/-0.5 m DEM range",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
        color="#475569",
    )


def make_figure3() -> None:
    style()
    arche = pd.read_csv(FIG_SOURCE / "Fig6_archetype_map_selection.csv")
    metrics = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    rows = arche.merge(
        metrics[
            [
                "station_id",
                "lat",
                "lon",
                "terrain_tiles",
            ]
        ],
        on="station_id",
        how="left",
    )
    n_rank = int(
        metrics[
            metrics["marine_seed_resolved"].eq(True)
            & metrics["match_dist_km"].le(6.0)
        ].dropna(subset=["coast_rp_rp10_m", "mask_connected_2m_lowland_pct"]).shape[0]
    )
    area_max = float(rows["connected_2m_area_km2"].max())
    cmap = ListedColormap([COLORS[k] for k in ["other", "coastal", "unconnected", "connected", "water", "capped"]])
    fig = plt.figure(figsize=(12.4, 9.4), constrained_layout=False)
    gs = fig.add_gridspec(3, 3, height_ratios=[1.12, 0.64, 0.82], hspace=0.27, wspace=0.20)
    for idx, row in rows.iterrows():
        ax = fig.add_subplot(gs[0, idx])
        cls, bbox, stats = classification_for_station(row)
        ax.imshow(cls, cmap=cmap, vmin=0, vmax=5, origin="upper", extent=[bbox[0], bbox[2], bbox[1], bbox[3]], interpolation="nearest")
        emphasize_connected_footprint(ax, cls, bbox, stats["connected_pct"])
        ax.plot(row["lon"], row["lat"], marker="*", ms=8.5, color="#DC2626", mec="white", mew=0.8)
        label = ARCHETYPE_LABELS.get(str(row["archetype"]), str(row["archetype"]))
        ax.set_title(
            f"{chr(97 + idx)}. {label}\n{short_station_name(row['station'])}",
            loc="left",
            fontweight="bold",
        )
        ax.set_xlabel("Longitude")
        if idx == 0:
            ax.set_ylabel("Latitude")
        else:
            ax.set_ylabel("")
        scale_bar(ax, float(row["lon"]), float(row["lat"]))
    legend_handles = [
        Patch(facecolor=COLORS["water"], label="Official marine-water network"),
        Patch(facecolor=COLORS["connected"], edgecolor="#075985", linewidth=1.2, label="Connected land below 2 m"),
        Patch(facecolor=COLORS["unconnected"], label="Unconnected land below 2 m"),
        Patch(facecolor=COLORS["coastal"], label="Other coastal-lowland land"),
        Patch(facecolor=COLORS["other"], edgecolor="#CBD5E1", label="Outside denominator / non-tidal water"),
        Patch(facecolor=COLORS["capped"], label="DeltaDTM clipped class 255"),
    ]
    fig.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=3, frameon=False)

    for idx, row in rows.iterrows():
        ax = fig.add_subplot(gs[1, idx])
        draw_evidence_card(ax, row, n_rank, area_max, ARCHETYPE_COLORS[idx], chr(100 + idx))

    for idx, row in rows.iterrows():
        ax = fig.add_subplot(gs[2, idx])
        draw_single_threshold_panel(ax, row, ARCHETYPE_COLORS[idx], chr(103 + idx))

    fig.subplots_adjust(left=0.055, right=0.985, top=0.900, bottom=0.065)
    fig.savefig(FIG_MAIN / "Fig3_connected_terrain_contrasts.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_MAIN / "Fig3_connected_terrain_contrasts.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_supplementary_gallery() -> None:
    style()
    metrics = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    gallery_ids = [
        "sheerness-p015-uk",
        "hoekvanholla-hvh-nl",
        "newlyn-p001-uk",
        "brest",
        "aberdeen-p038-uk",
        "dunkerque",
        "boulogne-sur-mer",
        "lowestoft-p024-uk",
        "delfzijl-del-nl",
    ]
    rows = metrics[metrics["station_id"].isin(gallery_ids)].copy()
    order = {sid: i for i, sid in enumerate(gallery_ids)}
    rows["gallery_order"] = rows["station_id"].map(order)
    rows = rows.sort_values("gallery_order")
    cmap = ListedColormap([COLORS[k] for k in ["other", "coastal", "unconnected", "connected", "water", "capped"]])
    fig = plt.figure(figsize=(12.3, 10.4), constrained_layout=False)
    gs = fig.add_gridspec(3, 3, hspace=0.28, wspace=0.16)
    for idx, (_, row) in enumerate(rows.iterrows()):
        ax = fig.add_subplot(gs[idx // 3, idx % 3])
        cls, bbox, stats = classification_for_station(row)
        ax.imshow(cls, cmap=cmap, vmin=0, vmax=5, origin="upper", extent=[bbox[0], bbox[2], bbox[1], bbox[3]], interpolation="nearest")
        emphasize_connected_footprint(ax, cls, bbox, stats["connected_pct"])
        ax.plot(row["lon"], row["lat"], marker="*", ms=8.0, color="#DC2626", mec="white", mew=0.8)
        ax.set_title(
            f"{chr(97 + idx)}. {short_station_name(row['station'])}\n"
            f"RP10 {float(row['coast_rp_rp10_m']):.2f} m; connected {stats['connected_pct']:.1f}%; "
            rf"area {stats['connected_area']:.2f} km$^2$",
            loc="left",
            fontweight="bold",
            fontsize=7.9,
        )
        if idx % 3 == 0:
            ax.set_ylabel("Latitude")
        else:
            ax.set_ylabel("")
        if idx // 3 == 2:
            ax.set_xlabel("Longitude")
        else:
            ax.set_xlabel("")
        scale_bar(ax, float(row["lon"]), float(row["lat"]), km=2.0)
    legend_handles = [
        Patch(facecolor=COLORS["water"], label="Official marine-water network"),
        Patch(facecolor=COLORS["connected"], edgecolor="#075985", linewidth=1.2, label="Connected land below 2 m"),
        Patch(facecolor=COLORS["unconnected"], label="Unconnected land below 2 m"),
        Patch(facecolor=COLORS["coastal"], label="Other coastal-lowland land"),
        Patch(facecolor=COLORS["other"], edgecolor="#CBD5E1", label="Outside denominator / non-tidal water"),
        Patch(facecolor=COLORS["capped"], label="DeltaDTM clipped class 255"),
    ]
    fig.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, 0.99), ncol=3, frameon=False)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.91, bottom=0.055)
    fig.savefig(FIG_MAIN / "FigS3_connectivity_gallery.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_MAIN / "FigS3_connectivity_gallery.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_figure4() -> None:
    style()
    rank = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv")
    assoc = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_two_sided_permutation_association.csv")
    block = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_sector_block_bootstrap.csv")
    topk = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_topk_overlap_null_envelope.csv")
    terrain = pd.read_csv(FIG_SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    main = terrain[
        terrain["marine_seed_resolved"].eq(True)
        & terrain["match_dist_km"].le(6.0)
    ].dropna(
        subset=["coast_rp_rp10_m", "mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"]
    ).copy()
    main["sample_type"] = np.where(main["archive_available"] & main["passes_years_ge25"] & main["passes_corr_ge055"], "GSSR-qualified", "spatial-only")

    fig = plt.figure(figsize=(11.8, 8.3), constrained_layout=False)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.92], hspace=0.34, wspace=0.28)
    ax_scatter = fig.add_subplot(gs[0, 0])
    colors = {"GSSR-qualified": "#0EA5E9", "spatial-only": "#94A3B8"}
    for label, sub in main.groupby("sample_type"):
        ax_scatter.scatter(
            sub["coast_rp_rp10_m"],
            sub["mask_connected_2m_lowland_pct"],
            s=np.clip(sub["mask_connected_2m_area_km2"] * 8 + 16, 18, 180),
            c=colors[label],
            alpha=0.78,
            edgecolor="white",
            lw=0.5,
            label=label,
        )
    for sid in ["avonmouth-p060-uk", "sheerness-p015-uk", "portpatrick-p063-uk", "delfzijl-del-nl"]:
        sub = main[main["station_id"].eq(sid)]
        if not sub.empty:
            r = sub.iloc[0]
            ax_scatter.text(
                r["coast_rp_rp10_m"] + 0.05,
                r["mask_connected_2m_lowland_pct"],
                str(r["station"]).split()[0],
                fontsize=6.7,
            )
    ax_scatter.set_xlabel("COAST-RP RP10 storm tide (m)")
    ax_scatter.set_ylabel("Connected lowland fraction at 2 m (%)")
    ax_scatter.set_title("a. Raw storm-tide magnitude versus connected-terrain response", loc="left", fontweight="bold")
    ax_scatter.grid(color="#E2E8F0", lw=0.6)
    ax_scatter.legend(frameon=False, loc="upper right")

    ax_topk = fig.add_subplot(gs[0, 1])
    sub = topk[
        (topk["sample"].eq("primary resolved mask-aware match<=6km"))
        & (topk["terrain_metric"].eq("mask_connected_2m_lowland_pct"))
    ]
    x = sub["top_fraction"] * 100
    ax_topk.fill_between(x, sub["null_overlap_p025"], sub["null_overlap_p975"], color="#CBD5E1", alpha=0.65, label="Permutation 95% envelope")
    ax_topk.plot(x, sub["null_overlap_p500"], color="#64748B", lw=1.5, ls="--", label="Permutation median")
    ax_topk.plot(x, sub["observed_overlap"], color="#0F172A", lw=2.1, marker="o", label="Observed")
    ax_topk.set_xlabel("Top-k threshold (% of sites)")
    ax_topk.set_ylabel("Top-set overlap (sites)")
    ax_topk.set_title("b. Observed top-k overlap relative to the permutation null", loc="left", fontweight="bold")
    ax_topk.grid(color="#E2E8F0", lw=0.6)
    ax_topk.legend(frameon=False, loc="upper left")
    top20 = sub[np.isclose(sub["top_fraction"], 0.20)].iloc[0]
    ax_topk.text(
        0.98,
        0.04,
        f"Top 20% overlap low-tail p={top20['overlap_low_tail_p']:.3f}",
        transform=ax_topk.transAxes,
        ha="right",
        va="bottom",
        color="#475569",
        fontsize=7.2,
    )

    ax_bar = fig.add_subplot(gs[1, 0])
    order = [
        "primary resolved mask-aware match<=6km",
        "all resolved mask-aware distance-unrestricted sensitivity",
        "GSSR-qualified primary mask-aware",
        "baseline 30-station primary sensitivity",
    ]
    plot = rank[
        rank["terrain_metric"].isin(["mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"])
    ].copy()
    plot["sample"] = pd.Categorical(plot["sample"], categories=order, ordered=True)
    plot = plot.sort_values(["sample", "terrain_metric"])
    y = np.arange(len(plot))
    color_metric = np.where(plot["terrain_metric"].eq("mask_connected_2m_lowland_pct"), "#0EA5E9", "#16A34A")
    ax_bar.barh(y, plot["spearman"], color=color_metric, alpha=0.86)
    ax_bar.axvline(0, color="#334155", lw=0.8)
    sample_labels = {
        "primary resolved mask-aware match<=6km": "Primary sample",
        "all resolved mask-aware distance-unrestricted sensitivity": "All resolved sites",
        "GSSR-qualified primary mask-aware": "GSSR-qualified",
        "baseline 30-station primary sensitivity": "Earlier 30-site subset",
    }
    clean_labels = []
    for s, m in zip(plot["sample"], plot["terrain_metric"]):
        clean_s = sample_labels.get(str(s), str(s))
        clean_m = "fraction" if str(m).endswith("lowland_pct") else "area"
        clean_labels.append(f"{clean_s}: {clean_m}")
    ax_bar.set_yticks(y, clean_labels)
    ax_bar.invert_yaxis()
    ax_bar.set_xlabel("Spearman rho: COAST-RP RP10 vs terrain metric")
    ax_bar.set_title("c. Fraction and area metrics give related but not identical rankings", loc="left", fontweight="bold")
    ax_bar.grid(axis="x", color="#E2E8F0", lw=0.6)
    ax_bar.legend(
        handles=[
            Patch(facecolor="#0EA5E9", label="Fraction"),
            Patch(facecolor="#16A34A", label="Area"),
        ],
        frameon=False,
        loc="lower left",
    )

    ax_unc = fig.add_subplot(gs[1, 1])
    primary_sample = "primary resolved mask-aware match<=6km"
    metric_specs = [
        ("Connected fraction", "mask_connected_2m_lowland_pct", "#0EA5E9"),
        ("Connected area", "mask_connected_2m_area_km2", "#16A34A"),
    ]
    for yi, (label, metric, color) in enumerate(metric_specs[::-1]):
        point = rank[(rank["sample"].eq(primary_sample)) & (rank["terrain_metric"].eq(metric))].iloc[0]
        interval = block[(block["sample"].eq(primary_sample)) & (block["terrain_metric"].eq(metric))].iloc[0]
        p_row = assoc[(assoc["sample"].eq(primary_sample)) & (assoc["terrain_metric"].eq(metric))].iloc[0]
        lo = float(interval["spearman_block_p025"])
        hi = float(interval["spearman_block_p975"])
        rho = float(point["spearman"])
        ax_unc.hlines(yi, lo, hi, color=color, lw=4.0, alpha=0.38)
        ax_unc.plot(rho, yi, marker="o", ms=7, color=color, mec="white", mew=0.8)
        annotation_y = yi - 0.17 if yi == 1 else yi + 0.17
        ax_unc.text(
            0.32,
            annotation_y,
            f"rho={rho:.2f}; site-label p={p_row['spearman_two_sided_p']:.3f}",
            ha="right",
            va="center",
            fontsize=7.5,
        )
    ax_unc.axvline(0, color="#111827", lw=0.9, ls="--")
    ax_unc.set_yticks([0, 1], ["Connected area", "Connected fraction"])
    ax_unc.set_xlim(-0.75, 0.35)
    ax_unc.set_xlabel("Spearman rho")
    ax_unc.set_title("d. Spatial resampling widens the association range", loc="left", fontweight="bold")
    ax_unc.grid(axis="x", color="#E2E8F0", lw=0.6)
    ax_unc.text(
        0.02,
        0.06,
        "Thick lines: six-sector block-resampling 95% range\n"
        "Points: station-level estimate; both spatial ranges cross zero",
        transform=ax_unc.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        color="#475569",
    )

    fig.subplots_adjust(left=0.075, right=0.985, top=0.965, bottom=0.065)
    fig.savefig(FIG_MAIN / "Fig2_regional_screening_agreement.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_MAIN / "Fig2_regional_screening_agreement.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    FIG_MAIN.mkdir(parents=True, exist_ok=True)
    make_figure3()
    make_supplementary_gallery()
    make_figure4()
    print("Wrote regional Figure 2, site-contrast Figure 3, and Supplementary Figure S3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

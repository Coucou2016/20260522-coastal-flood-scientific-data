#!/usr/bin/env python3
"""Build the post-review manuscript figures from the frozen analysis tables.

The figures deliberately distinguish lowland prevalence, conditional raster
connectivity and connected area. They never enlarge classified cells or label
the static terrain screen as inundation. Every plotted value is exported to a
machine-readable source table alongside the figure.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from add_advanced_terrain_rank_diagnostics import (  # noqa: E402
    cell_area_km2,
    fixed_km_bbox,
    read_dem_window_fast,
    sum_area,
)
from add_mask_aware_terrain_diagnostics import resolve_marine_seed  # noqa: E402
from inundation_sensitivity import valid_mask  # noqa: E402
from make_cee_main_figures import draw_tile_basemap, lonlat_to_mercator  # noqa: E402
from publication_style import apply_publication_style  # noqa: E402
from rebuild_frozen_primary_analysis import classify  # noqa: E402


FIG_SOURCE = ROOT / "data" / "figure_source"
FIG_MAIN = ROOT / "figures" / "main"

PRIMARY = FIG_SOURCE / "Primary_terrain_components_68stations.csv"
ROBUSTNESS = FIG_SOURCE / "Terrain_robustness_grid_74stations.csv"
LOCAL_CROSSCHECK = FIG_SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv"

SECTOR_COLORS = {
    "Atlantic-Celtic": "#2A6FBB",
    "western-English-Channel": "#00A087",
    "eastern-Channel-southern-North-Sea": "#E07A1F",
    "British-North-Sea": "#7A5195",
    "Dutch-German-Bight": "#C44536",
    "Denmark-Norway": "#5B6770",
}

CLASS_COLORS = {
    "other_land": "#E8E8E8",
    "unconnected": "#E69F00",
    "connected": "#0072B2",
    "tidal_water": "#B9DDF2",
    "other_water": "#C9D2D8",
    "excluded": "#FFFFFF",
}

METRIC_LABELS = {
    "connected_reference_land_pct": "Connected share of represented land",
    "below_reference_land_pct": "Land below 2 m",
    "conditional_connectivity_pct": "Connected share of below-2 m land",
    "connected_area_km2": "Connected area",
}


def style() -> None:
    apply_publication_style()
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8.5,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    FIG_MAIN.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_MAIN / f"{stem}.png", dpi=500, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_MAIN / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def panel(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.08,
        1.04,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )


def short_name(value: str) -> str:
    text = str(value)
    replacements = {
        "Lowestoft P024 Uk": "Lowestoft",
        "Newport P057 Uk": "Newport",
        "Immingham P026 Uk": "Immingham",
        "Saint Nazaire France": "Saint-Nazaire",
        "Delfzijl Del Nl": "Delfzijl",
        "Denhelder Hel Nl": "Den Helder",
        "Hoek van Holland": "Hoek van Holland",
        "Sheerness": "Sheerness",
    }
    text = replacements.get(text, text.replace(" France", "").replace(" Germany", ""))
    text = re.sub(r"\s+P\d+\s+Uk$", "", text)
    return text.replace("Milfordhaven", "Milford Haven")


def repelled_station_labels(ax: plt.Axes, frame: pd.DataFrame, x: str, y: str) -> None:
    texts = [
        ax.text(float(row[x]), float(row[y]), short_name(row["station"]), fontsize=5.7, ha="left", va="bottom")
        for _, row in frame.iterrows()
    ]
    adjust_text(
        texts,
        x=frame[x].to_numpy(float),
        y=frame[y].to_numpy(float),
        ax=ax,
        ensure_inside_axes=True,
        prevent_crossings=True,
        expand=(1.08, 1.18),
        force_text=(0.18, 0.28),
        force_static=(0.10, 0.18),
        arrowprops={"arrowstyle": "-", "color": "#6B7280", "lw": 0.35},
        time_lim=2,
    )


def format_mercator_axes(ax: plt.Axes, lons: list[float], lats: list[float]) -> None:
    xticks = [lonlat_to_mercator(v, 50.0)[0] for v in lons]
    yticks = [lonlat_to_mercator(0.0, v)[1] for v in lats]
    ax.set_xticks(xticks, [f"{abs(v):g}°{'E' if v >= 0 else 'W'}" for v in lons])
    ax.set_yticks(yticks, [f"{abs(v):g}°N" for v in lats])
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")


def figure1() -> None:
    style()
    primary = pd.read_csv(PRIMARY)
    flow = pd.read_csv(FIG_SOURCE / "Primary_sample_flow.csv")
    metric = "connected_reference_land_pct"
    k = math.ceil(0.2 * len(primary))
    water_top = set(primary.nlargest(k, "coast_rp_rp10_m")["station_id"])
    terrain_top = set(primary.nlargest(k, metric)["station_id"])
    primary["water_top20"] = primary["station_id"].isin(water_top)
    primary["terrain_top20"] = primary["station_id"].isin(terrain_top)
    primary.to_csv(FIG_SOURCE / "Fig1_primary_station_map_source.csv", index=False)

    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 0.72], wspace=0.16)
    ax = fig.add_subplot(gs[0, 0])
    draw_tile_basemap(ax, (-10.0, 10.0, 46.5, 61.5), zoom=5)
    for sector, group in primary.groupby("coastal_sector"):
        xy = np.array([lonlat_to_mercator(float(x), float(y)) for x, y in zip(group["lon"], group["lat"])])
        ax.scatter(
            xy[:, 0],
            xy[:, 1],
            s=31,
            c=SECTOR_COLORS[sector],
            edgecolors="white",
            linewidths=0.6,
            label=f"{sector.replace('-', ' ')} (n={len(group)})",
            zorder=6,
        )
    for _, row in primary[primary["water_top20"] | primary["terrain_top20"]].iterrows():
        x, y = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
        marker = "*" if row["water_top20"] and row["terrain_top20"] else ("^" if row["water_top20"] else "s")
        ax.plot(x, y, marker=marker, ms=7.2, mfc="none", mec="#111111", mew=1.0, ls="None", zorder=8)
    format_mercator_axes(ax, [-8, -4, 0, 4, 8], [48, 52, 56, 60])
    ax.set_title("Northwest European station inventory and coastal sectors", loc="left", fontweight="bold")
    panel(ax, "a")
    sector_legend = ax.legend(loc="lower left", frameon=True, framealpha=0.95, fontsize=6.4, ncol=1)
    ax.add_artist(sector_legend)
    ax.legend(
        handles=[
            Line2D([], [], marker="^", mfc="none", mec="#111111", ls="None", label="Storm-tide top 20%"),
            Line2D([], [], marker="s", mfc="none", mec="#111111", ls="None", label="Terrain top 20%"),
            Line2D([], [], marker="*", mfc="none", mec="#111111", ls="None", label="Both"),
        ],
        loc="upper right",
        frameon=True,
        framealpha=0.95,
        fontsize=6.5,
    )
    ax.text(
        0.01,
        0.01,
        "Basemap: CARTO/© OpenStreetMap contributors",
        transform=ax.transAxes,
        fontsize=5.8,
        color="#4B5563",
        ha="left",
        va="bottom",
    )

    axf = fig.add_subplot(gs[0, 1])
    axf.set_axis_off()
    axf.set_title("Analytical sample flow", loc="left", fontweight="bold")
    panel(axf, "b")
    y = np.linspace(0.85, 0.18, len(flow))
    short_stage = {
        "GSSR metadata stations inside geographic bounds": "Regional candidate stations",
        "DeltaDTM v1.1 elevation tiles available": "DeltaDTM v1.1.1 support",
        "Official marine seed resolved in 10 km window/context": "Official marine seed resolved",
        "COAST-RP nearest match within 6 km (primary)": "COAST-RP match within 6 km",
        "GSSR record >=25 years and reconstruction correlation >=0.55": "GSSR-qualified subset",
    }
    for i, (_, row) in enumerate(flow.iterrows()):
        axf.add_patch(
            plt.Rectangle((0.08, y[i] - 0.050), 0.78, 0.10, transform=axf.transAxes, facecolor="#D9EAF4", edgecolor="#3976A8", lw=0.8)
        )
        axf.text(0.11, y[i], short_stage.get(str(row["stage"]), str(row["stage"])), transform=axf.transAxes, ha="left", va="center", fontsize=6.6)
        axf.text(0.83, y[i], f"n={int(row['n'])}", transform=axf.transAxes, ha="right", va="center", fontsize=7.0, fontweight="bold")
        if i < len(flow) - 1:
            axf.annotate("", xy=(0.45, y[i + 1] + 0.055), xytext=(0.45, y[i] - 0.055), xycoords=axf.transAxes, arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#6B7280"})
    axf.text(
        0.08,
        0.04,
        "The regional ranking is drawn from the GSSR station inventory, but it does not require a GSSR return-level estimate.",
        transform=axf.transAxes,
        ha="left",
        va="bottom",
        fontsize=6.4,
        color="#4B5563",
        wrap=True,
    )
    fig.subplots_adjust(left=0.075, right=0.985, top=0.93, bottom=0.10)
    save(fig, "Fig1_process_terrain_design")


def figure2() -> None:
    style()
    primary = pd.read_csv(PRIMARY)
    rank = pd.read_csv(FIG_SOURCE / "Rank_robustness_one_at_a_time.csv")
    block = pd.read_csv(FIG_SOURCE / "Spatial_sector_bootstrap_intervals.csv")
    topk = pd.read_csv(FIG_SOURCE / "Topk_spatial_null_curves.csv")
    return_period = pd.read_csv(FIG_SOURCE / "Return_period_sensitivity.csv")
    primary_setting = "primary:10km,2m,4n,adaptive,match<=6km"
    base = rank[rank["setting"].eq(primary_setting)].copy()
    base.to_csv(FIG_SOURCE / "Fig2_primary_association_source.csv", index=False)

    fig = plt.figure(figsize=(7.35, 7.0))
    gs = fig.add_gridspec(2, 2, hspace=0.36, wspace=0.48)

    ax = fig.add_subplot(gs[0, 0])
    for sector, group in primary.groupby("coastal_sector"):
        ax.scatter(
            group["coast_rp_rp10_m"],
            group["connected_reference_land_pct"],
            s=28,
            color=SECTOR_COLORS[sector],
            alpha=0.78,
            edgecolor="white",
            linewidth=0.45,
            label=sector.replace("-", " "),
        )
    for sid in ["newport-p057-uk", "lowestoft-p024-uk", "delfzijl-del-nl"]:
        row = primary[primary["station_id"].eq(sid)].iloc[0]
        ax.annotate(short_name(row["station"]), (row["coast_rp_rp10_m"], row["connected_reference_land_pct"]), xytext=(3, 3), textcoords="offset points", fontsize=6.2)
    ax.set_xlabel("COAST-RP 10-year storm tide (m)")
    ax.set_ylabel("Connected share of represented land (%)")
    ax.set_yscale("log")
    ax.set_yticks([0.1, 1, 10, 100], ["0.1", "1", "10", "100"])
    ax.grid(True, which="major", color="#D1D5DB", lw=0.45)
    ax.set_title("Station-level association", loc="left", fontweight="bold")
    panel(ax, "a")

    ax = fig.add_subplot(gs[0, 1])
    spatial = return_period[return_period["return_period_years"].eq(10)][
        ["terrain_metric", "sector_stratified_permutation_two_sided_p"]
    ]
    plot = base.merge(block, on=["setting", "terrain_metric"], suffixes=("", "_block")).merge(
        spatial, on="terrain_metric", how="left"
    )
    y = np.arange(len(plot))[::-1]
    for yi, (_, row) in zip(y, plot.iterrows()):
        ax.hlines(yi, row["spearman_sector_bootstrap_p025"], row["spearman_sector_bootstrap_p975"], color="#9CA3AF", lw=4.0)
        ax.plot(row["spearman"], yi, "o", color="#1F4E79", mec="white", mew=0.6, ms=6.5)
        p_value = float(row["sector_stratified_permutation_two_sided_p"])
        p_text = "sector p<0.001" if p_value < 0.001 else f"sector p={p_value:.3f}"
        ax.text(0.29, yi, p_text, ha="right", va="center", fontsize=6.1)
    ax.axvline(0, color="#111111", lw=0.8, ls="--")
    compact_metric_labels = {
        "connected_reference_land_pct": "Connected land share",
        "below_reference_land_pct": "Below-2 m land share",
        "conditional_connectivity_pct": "Conditional connection",
        "connected_area_km2": "Connected area",
    }
    ax.set_yticks(y, [""] * len(y))
    for yi, metric in zip(y, plot["terrain_metric"]):
        ax.text(-0.72, yi + 0.13, compact_metric_labels[metric], ha="left", va="bottom", fontsize=6.6)
    ax.set_xlim(-0.75, 0.32)
    ax.set_xlabel("Spearman correlation")
    ax.set_title("Sensitivity to coastal-sector resampling", loc="left", fontweight="bold")
    panel(ax, "b")

    ax = fig.add_subplot(gs[1, 0])
    curve = topk.copy()
    x = curve["top_share_pct"]
    ax.fill_between(x, curve["sector_stratified_null_q025"], curve["sector_stratified_null_q975"], color="#D1D5DB", alpha=0.75, label="Within-sector null 95% envelope")
    ax.plot(x, curve["sector_stratified_null_median"], color="#6B7280", ls="--", lw=1.3, label="Within-sector null median")
    ax.plot(x, curve["observed_overlap"], color="#0072B2", marker="o", lw=1.8, label="Observed")
    ax.set_xlabel("Top-set size (% of stations)")
    ax.set_ylabel("Number of shared stations")
    ax.set_title("Top-set overlap remains inside the spatial null envelope", loc="left", fontweight="bold")
    ax.grid(True, color="#D1D5DB", lw=0.45)
    ax.legend(frameon=False, loc="upper left", fontsize=6.5)
    panel(ax, "c")

    ax = fig.add_subplot(gs[1, 1])
    rp_colors = {
        "lowland_prevalence": "#E69F00",
        "conditional_connectivity": "#009E73",
        "connected_lowland_share": "#0072B2",
        "connected_area": "#7A5195",
    }
    for label, group in return_period[
        return_period["terrain_metric_label"].isin(rp_colors)
    ].groupby("terrain_metric_label", sort=False):
        ax.plot(
            group["return_period_years"],
            group["spearman"],
            marker="o",
            ms=4.2,
            lw=1.5,
            color=rp_colors[label],
            label=label.replace("_", " "),
        )
    ax.axhline(0, color="#111111", lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_xticks(list((2, 5, 10, 25, 50, 100)), ["2", "5", "10", "25", "50", "100"])
    ax.set_ylim(-0.48, 0.22)
    ax.set_xlabel("COAST-RP return period (years)")
    ax.set_ylabel("Spearman correlation")
    ax.set_title("Association persists from RP2 to RP100", loc="left", fontweight="bold")
    ax.grid(True, color="#D1D5DB", lw=0.45)
    ax.legend(frameon=False, loc="lower right", fontsize=6.1)
    panel(ax, "d")

    fig.subplots_adjust(left=0.105, right=0.965, top=0.95, bottom=0.08)
    save(fig, "Fig2_regional_screening_agreement")


def select_figure3_sites(primary: pd.DataFrame, local: pd.DataFrame) -> pd.DataFrame:
    frame = primary.copy()
    n = len(frame)
    k = math.ceil(0.2 * n)
    frame["water_rank"] = frame["coast_rp_rp10_m"].rank(ascending=False, method="min").astype(int)
    frame["terrain_rank"] = frame["connected_reference_land_pct"].rank(ascending=False, method="min").astype(int)
    frame["rank_displacement"] = frame["terrain_rank"] - frame["water_rank"]

    stable = frame.merge(
        local[["station_id", "connected_pixel_iou_after_reprojection", "fraction_difference_local_minus_delta_pct_points"]],
        on="station_id",
    )
    stable = stable[(stable["terrain_rank"] <= k) & stable["connected_pixel_iou_after_reprojection"].ge(0.75)].copy()
    stable["absolute_product_difference"] = stable["fraction_difference_local_minus_delta_pct_points"].abs()
    stable_case = stable.sort_values(["absolute_product_difference", "terrain_rank"]).iloc[0]

    lowland_limited = frame[(frame["water_rank"] <= k) & frame["conditional_connectivity_pct"].ge(90)].copy()
    lowland_case = lowland_limited.sort_values(["rank_displacement", "water_rank"], ascending=[False, True]).iloc[0]

    median_below = float(frame["below_reference_land_pct"].median())
    connectivity_filtered = frame[frame["below_reference_land_pct"].ge(median_below)].copy()
    filtered_case = connectivity_filtered.sort_values(["conditional_connectivity_pct", "below_reference_land_pct"], ascending=[True, False]).iloc[0]

    rows = []
    for role, rule, row in [
        (
            "stable terrain-priority case",
            "Top-20% connected-land share, local-DTM IoU >= 0.75; smallest absolute local-minus-DeltaDTM share difference",
            stable_case,
        ),
        (
            "water-priority, lowland-limited case",
            "Top-20% storm tide and conditional connectivity >= 90%; maximum terrain-minus-water rank displacement, then highest water rank",
            lowland_case,
        ),
        (
            "connectivity-filtered case",
            "Below-2 m land share at or above the sample median; minimum conditional connectivity",
            filtered_case,
        ),
    ]:
        record = row.to_dict()
        record["figure3_role"] = role
        record["selection_rule"] = rule
        rows.append(record)
    selected = pd.DataFrame(rows)
    selected.to_csv(FIG_SOURCE / "Fig3_predefined_site_selection.csv", index=False)
    return selected


def station_layers(row: pd.Series, level: float = 2.0, offset: float = 0.0) -> tuple[np.ndarray, tuple[float, float, float, float], dict[str, float]]:
    bbox = fixed_km_bbox(float(row["lon"]), float(row["lat"]), 10.0)
    lon2d, lat2d, elev, _, meta, _ = read_dem_window_fast(bbox)
    valid = valid_mask(elev)
    mask, tidal, _ = resolve_marine_seed(float(row["lon"]), float(row["lat"]), bbox, elev.shape, meta["transform"], meta["crs"])
    area = cell_area_km2(lon2d, lat2d)
    result = classify(elev, valid, mask, area, tidal, level, 4, elevation_offset_m=offset)
    effective = elev + offset
    below = valid & (mask == 0) & np.isfinite(effective) & (effective <= level)
    connected_result = classify(elev, valid, mask, area, tidal, level, 4, elevation_offset_m=offset)
    passable = below | tidal
    from scipy import ndimage as ndi

    connected = ndi.binary_propagation(tidal, structure=ndi.generate_binary_structure(2, 1), mask=passable) & below
    classes = np.full(elev.shape, 5, dtype=np.uint8)
    classes[valid & (mask == 0)] = 0
    classes[below & ~connected] = 1
    classes[connected] = 2
    classes[tidal] = 3
    classes[(mask == 2) | ((mask == 3) & ~tidal)] = 4
    return classes, bbox, {k: float(v) for k, v in connected_result.items() if isinstance(v, (float, np.floating))}


def threshold_curves(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, station in selected.iterrows():
        for level in np.arange(0.0, 3.01, 0.25):
            values = {}
            for offset, label in [(0.0, "baseline"), (-0.5, "offset_minus_0p5m"), (0.5, "offset_plus_0p5m")]:
                _, _, result = station_layers(station, float(level), offset)
                values[label] = result
            rows.append(
                {
                    "station_id": station["station_id"],
                    "station": station["station"],
                    "level_m": level,
                    "below_reference_land_pct": values["baseline"]["below_reference_land_pct"],
                    "connected_reference_land_pct": values["baseline"]["connected_reference_land_pct"],
                    "conditional_connectivity_pct": values["baseline"]["conditional_connectivity_pct"],
                    "connected_offset_minus_0p5m_pct": values["offset_minus_0p5m"]["connected_reference_land_pct"],
                    "connected_offset_plus_0p5m_pct": values["offset_plus_0p5m"]["connected_reference_land_pct"],
                    "connected_offset_range_min_pct": min(values["offset_minus_0p5m"]["connected_reference_land_pct"], values["offset_plus_0p5m"]["connected_reference_land_pct"]),
                    "connected_offset_range_max_pct": max(values["offset_minus_0p5m"]["connected_reference_land_pct"], values["offset_plus_0p5m"]["connected_reference_land_pct"]),
                }
            )
    output = pd.DataFrame(rows)
    output.to_csv(FIG_SOURCE / "Fig3_threshold_response_source.csv", index=False)
    return output


def map_panel(ax: plt.Axes, row: pd.Series, label: str) -> None:
    classes, bbox, _ = station_layers(row)
    cmap = ListedColormap([CLASS_COLORS[x] for x in ["other_land", "unconnected", "connected", "tidal_water", "other_water", "excluded"]])
    km_lon = 111.32 * math.cos(math.radians(float(row["lat"])))
    extent_km = [
        (bbox[0] - float(row["lon"])) * km_lon,
        (bbox[2] - float(row["lon"])) * km_lon,
        (bbox[1] - float(row["lat"])) * 110.574,
        (bbox[3] - float(row["lat"])) * 110.574,
    ]
    ax.imshow(classes, cmap=cmap, vmin=0, vmax=5, origin="upper", extent=extent_km, interpolation="nearest")
    connected = classes == 2
    if connected.any():
        ax.contour(connected.astype(float), levels=[0.5], colors=["#003B66"], linewidths=0.65, origin="upper", extent=extent_km)
    ax.plot(0, 0, marker="*", ms=7.5, color="#B22222", mec="white", mew=0.6)
    ax.set_title(f"{label} {short_name(row['station'])}\n{row['figure3_role'].capitalize()}", loc="left", fontweight="bold")
    ax.set_xlabel("Local easting from gauge (km)")
    ax.set_ylabel("Local northing from gauge (km)")
    bar_y = extent_km[2] + 0.55
    bar_x0 = extent_km[0] + 0.55
    ax.plot([bar_x0, bar_x0 + 2.0], [bar_y, bar_y], color="#111111", lw=2.0, solid_capstyle="butt")
    ax.text(bar_x0 + 1.0, bar_y + 0.18, "2 km", ha="center", va="bottom", fontsize=6.2)
    if float(row["connected_reference_land_pct"]) < 1.0 and connected.any():
        rr, cc = np.where(connected)
        pad = 8
        r0, r1 = max(int(rr.min()) - pad, 0), min(int(rr.max()) + pad + 1, classes.shape[0])
        c0, c1 = max(int(cc.min()) - pad, 0), min(int(cc.max()) + pad + 1, classes.shape[1])
        inset = ax.inset_axes([0.60, 0.05, 0.36, 0.36])
        inset.imshow(classes[r0:r1, c0:c1], cmap=cmap, vmin=0, vmax=5, origin="upper", interpolation="nearest")
        inset.contour((classes[r0:r1, c0:c1] == 2).astype(float), levels=[0.5], colors=["#003B66"], linewidths=0.8, origin="upper")
        inset.set_xticks([])
        inset.set_yticks([])
        inset.set_title("Connected cells (zoom)", fontsize=5.8, pad=1.5)


def figure3() -> None:
    style()
    primary = pd.read_csv(PRIMARY)
    local = pd.read_csv(LOCAL_CROSSCHECK)
    selected = select_figure3_sites(primary, local)
    curves = threshold_curves(selected)
    fig = plt.figure(figsize=(7.2, 8.0))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.18, 0.72, 0.82], hspace=0.35, wspace=0.25)

    for i, (_, row) in enumerate(selected.iterrows()):
        ax = fig.add_subplot(gs[0, i])
        map_panel(ax, row, f"{chr(97 + i)}.")

    component_colors = ["#56B4E9", "#009E73", "#0072B2"]
    for i, (_, row) in enumerate(selected.iterrows()):
        ax = fig.add_subplot(gs[1, i])
        values = [row["below_reference_land_pct"], row["conditional_connectivity_pct"], row["connected_reference_land_pct"]]
        names = ["Below 2 m\nland share", "Conditional\nconnection", "Connected\nland share"]
        bars = ax.bar(np.arange(3), values, color=component_colors, width=0.66)
        ax.set_ylim(0, 105)
        ax.set_xticks(np.arange(3), names)
        ax.set_ylabel("Percent")
        ax.grid(axis="y", color="#D1D5DB", lw=0.45)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, max(value + 2.2, 3.0), f"{value:.2f}%", ha="center", va="bottom", fontsize=6.5)
        ax.set_title(f"{chr(100 + i)}. Why the connected share is high or low", loc="left", fontweight="bold")
        ax.text(0.98, 0.73, f"RP10 {row['coast_rp_rp10_m']:.2f} m\nwater rank {int(row['water_rank'])}/68\nterrain rank {int(row['terrain_rank'])}/68\narea {row['connected_area_km2']:.2f} km²", transform=ax.transAxes, ha="right", va="top", fontsize=6.2, color="#374151", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.5})

    for i, (_, row) in enumerate(selected.iterrows()):
        ax = fig.add_subplot(gs[2, i])
        sub = curves[curves["station_id"].eq(row["station_id"])]
        ax.plot(sub["level_m"], sub["below_reference_land_pct"], color="#E69F00", lw=1.5, label="Below-threshold land")
        ax.plot(sub["level_m"], sub["connected_reference_land_pct"], color="#0072B2", lw=1.8, label="Connected land")
        ax.plot(sub["level_m"], sub["connected_offset_minus_0p5m_pct"], color="#0072B2", lw=0.9, ls="--", label="Connected, DEM -0.5 m")
        ax.plot(sub["level_m"], sub["connected_offset_plus_0p5m_pct"], color="#0072B2", lw=0.9, ls=":", label="Connected, DEM +0.5 m")
        ax.axvline(2.0, color="#4B5563", ls="--", lw=0.8)
        ax.set_yscale("symlog", linthresh=0.1, linscale=0.8)
        ax.set_ylim(0, 110)
        ax.set_yticks([0, 0.1, 1, 10, 100], ["0", "0.1", "1", "10", "100"])
        ax.set_xlim(0, 3)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xlabel("Threshold (m EGM2008)")
        ax.set_ylabel("Share of represented land (%)")
        ax.grid(True, which="major", color="#D1D5DB", lw=0.45)
        ax.set_title(f"{chr(103 + i)}. Threshold response", loc="left", fontweight="bold")
        if i == 0:
            ax.legend(frameon=False, loc="upper left", fontsize=6.3)

    fig.legend(
        handles=[
            Patch(facecolor=CLASS_COLORS["tidal_water"], label="Ocean-connected water seed"),
            Patch(facecolor=CLASS_COLORS["connected"], edgecolor="#003B66", label="Connected land below 2 m"),
            Patch(facecolor=CLASS_COLORS["unconnected"], label="Unconnected land below 2 m"),
            Patch(facecolor=CLASS_COLORS["other_land"], label="Other represented land"),
            Patch(facecolor=CLASS_COLORS["other_water"], label="Lake/non-tidal water"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=3,
        frameon=False,
        fontsize=6.7,
    )
    fig.text(0.5, 0.018, "Thresholds are standardized terrain elevations in EGM2008, not event-specific flood water levels.", ha="center", va="bottom", fontsize=6.8, color="#4B5563")
    fig.subplots_adjust(left=0.075, right=0.985, top=0.925, bottom=0.085)
    save(fig, "Fig3_connected_terrain_contrasts")


def figure4() -> None:
    style()
    primary = pd.read_csv(PRIMARY)
    denominator = pd.read_csv(FIG_SOURCE / "Denominator_geometry_68stations.csv")
    topology = pd.read_csv(FIG_SOURCE / "Topology_membership_changes.csv")
    topology_summary = pd.read_csv(FIG_SOURCE / "Topology_sensitivity_summary.csv")
    rank = pd.read_csv(FIG_SOURCE / "Rank_robustness_one_at_a_time.csv")

    fig = plt.figure(figsize=(7.35, 7.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[0.83, 1.35], hspace=0.42, wspace=0.40)

    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(
        primary["below_reference_land_pct"],
        primary["conditional_connectivity_pct"],
        color="#4C78A8",
        s=27,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.set_xscale("log")
    ax.set_xlabel("Land below 2 m EGM2008 (%)")
    ax.set_ylabel("Conditional connectivity (%)")
    ax.set_title("Terrain metric components", loc="left", fontweight="bold", fontsize=8.0)
    ax.grid(True, color="#D1D5DB", lw=0.45)
    panel(ax, "a")

    ax = fig.add_subplot(gs[0, 1])
    for sector, group in denominator.groupby("coastal_sector"):
        ax.scatter(
            group["represented_land_window_pct"],
            group["connected_reference_land_pct"],
            s=25,
            color=SECTOR_COLORS[sector],
            edgecolor="white",
            linewidth=0.4,
            alpha=0.82,
        )
    raw = float(stats.spearmanr(denominator["represented_land_window_pct"], denominator["connected_reference_land_pct"]).statistic)
    ax.set_yscale("log")
    ax.set_xlabel("Represented land in nominal 10 km window (%)")
    ax.set_ylabel("Connected share of represented land (%)")
    ax.set_title("Represented-land coverage", loc="left", fontweight="bold", fontsize=8.0)
    ax.text(0.04, 0.94, f"Spearman ρ={raw:.2f}", transform=ax.transAxes, ha="left", va="top", fontsize=6.8)
    ax.grid(True, color="#D1D5DB", lw=0.45)
    panel(ax, "b")

    ax = fig.add_subplot(gs[0, 2])
    topo = topology[topology["terrain_metric"].eq("connected_reference_land_pct")].copy()
    changed = topo["membership_change"].ne("unchanged")
    ax.scatter(topo.loc[~changed, "four_neighbour_value"], topo.loc[~changed, "eight_neighbour_value"], s=24, color="#7A9E9F", edgecolor="white", linewidth=0.4, label="Top-set status unchanged")
    ax.scatter(topo.loc[changed, "four_neighbour_value"], topo.loc[changed, "eight_neighbour_value"], s=38, color="#D55E00", edgecolor="white", linewidth=0.5, label="Top-set membership changed")
    limits = [0.08, 120]
    ax.plot(limits, limits, color="#111111", ls="--", lw=0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_xlabel("4-neighbour primary share (%)")
    ax.set_ylabel("8-neighbour sensitivity share (%)")
    summary = topology_summary[topology_summary["terrain_metric"].eq("connected_reference_land_pct")].iloc[0]
    ax.set_title("4- versus 8-neighbour connectivity", loc="left", fontweight="bold", fontsize=8.0)
    ax.text(0.04, 0.96, f"rank ρ={summary['rank_spearman_4n_vs_8n']:.2f}\n{int(summary['membership_changes'])} membership changes", transform=ax.transAxes, ha="left", va="top", fontsize=6.5)
    ax.legend(frameon=False, loc="lower right", fontsize=5.8)
    ax.grid(True, color="#D1D5DB", lw=0.45)
    panel(ax, "c")

    ax = fig.add_subplot(gs[1, :])
    primary_setting = "primary:10km,2m,4n,adaptive,match<=6km"
    settings = [
        primary_setting,
        "window:5km",
        "window:20km",
        "threshold:1m",
        "threshold:3m",
        "neighbours:8",
        "seed:local-ocean-only",
        "uniform-elevation-offset:-1m",
        "uniform-elevation-offset:-0.5m",
        "uniform-elevation-offset:+0.5m",
        "uniform-elevation-offset:+1m",
        "COAST-match:<=1km",
        "COAST-match:<=2km",
        "COAST-match:distance-unrestricted",
    ]
    labels = [
        "Primary: 10 km, 2 m, 4n",
        "Window 5 km",
        "Window 20 km",
        "Threshold 1 m",
        "Threshold 3 m",
        "8-neighbour",
        "Local ocean only",
        "DEM offset -1 m",
        "DEM offset -0.5 m",
        "DEM offset +0.5 m",
        "DEM offset +1 m",
        "COAST match <=1 km",
        "COAST match <=2 km",
        "COAST match unrestricted",
    ]
    columns = ["connected_reference_land_pct", "below_reference_land_pct", "conditional_connectivity_pct", "connected_area_km2"]
    heat = rank[rank["setting"].isin(settings)].pivot(index="setting", columns="terrain_metric", values="spearman").reindex(settings)
    values = heat[columns].to_numpy(float)
    image = ax.imshow(values, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=6.0)
    ax.set_yticks(np.arange(len(labels)), labels, fontsize=6.4)
    ax.set_xticks(np.arange(4), ["Connected land share", "Below-2 m land share", "Conditional connection", "Connected area"])
    ax.set_title("One-at-a-time analysis sensitivity", loc="left", fontweight="bold")
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Spearman correlation", fontsize=7.0)
    panel(ax, "d")

    fig.subplots_adjust(left=0.17, right=0.975, top=0.965, bottom=0.08)
    save(fig, "Fig4_metric_decomposition_robustness")


def supplementary_local_dtm() -> None:
    style()
    frame = pd.read_csv(LOCAL_CROSSCHECK)
    frame["label"] = frame["station"].map(short_name)
    frame.to_csv(FIG_SOURCE / "FigS4_local_dtm_crosscheck_source.csv", index=False)
    y = np.arange(len(frame))[::-1]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0), gridspec_kw={"hspace": 0.36, "wspace": 0.32})

    def paired(ax: plt.Axes, delta_col: str, local_col: str, xlabel: str, label: str) -> None:
        for yi, (_, row) in zip(y, frame.iterrows()):
            ax.plot([row[delta_col], row[local_col]], [yi, yi], color="#9CA3AF", lw=1.5)
        ax.scatter(frame[delta_col], y, color="#0072B2", marker="o", label="DeltaDTM v1.1.1", zorder=3)
        ax.scatter(frame[local_col], y, color="#D55E00", marker="s", label="National/local DTM", zorder=3)
        ax.set_yticks(y, frame["label"])
        ax.set_xscale("log")
        ax.set_xlabel(xlabel)
        ax.grid(axis="x", color="#D1D5DB", lw=0.45)
        ax.set_title(label, loc="left", fontweight="bold")

    paired(axes[0, 0], "delta_connected_2m_reference_land_pct", "local_connected_2m_reference_land_pct", "Connected share (%)", "a. Connected share of represented land")
    axes[0, 0].set_xlim(0.15, 130)
    paired(axes[0, 1], "delta_connected_2m_area_km2", "local_connected_2m_area_km2", "Connected area (km²)", "b. Absolute connected area")
    axes[0, 1].set_xlim(0.035, 90)

    ax = axes[1, 0]
    ax.barh(y, frame["connected_pixel_iou_after_reprojection"], color="#4C78A8")
    ax.set_yticks(y, frame["label"])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Intersection over union")
    ax.set_title("c. Spatial overlap on the local-DTM grid", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#D1D5DB", lw=0.45)

    ax = axes[1, 1]
    dx = frame["local_below_2m_reference_land_pct"] - frame["delta_below_2m_reference_land_pct"]
    dc = frame["local_conditional_connectivity_2m_pct"] - frame["delta_conditional_connectivity_2m_pct"]
    ax.scatter(dx, dc, color="#6A3D9A", s=30)
    labels = [ax.text(float(x), float(z), name, fontsize=5.8, ha="left", va="bottom") for x, z, name in zip(dx, dc, frame["label"])]
    ax.axhline(0, color="#6B7280", lw=0.8)
    ax.axvline(0, color="#6B7280", lw=0.8)
    ax.set_xlim(-17.8, 3.0)
    ax.set_ylim(-99, 7)
    ax.set_xlabel("Change in below-2 m land share\n(local minus DeltaDTM, percentage points)")
    ax.set_ylabel("Change in conditional connection\n(percentage points)")
    ax.set_title("d. Product/datum differences alter both components", loc="left", fontweight="bold")
    ax.grid(True, color="#D1D5DB", lw=0.45)
    adjust_text(
        labels,
        x=dx.to_numpy(float),
        y=dc.to_numpy(float),
        ax=ax,
        ensure_inside_axes=True,
        prevent_crossings=True,
        expand=(1.08, 1.18),
        force_text=(0.15, 0.30),
        arrowprops={"arrowstyle": "-", "color": "#6B7280", "lw": 0.35},
        time_lim=2,
    )

    fig.legend(
        handles=[
            Line2D([], [], marker="o", color="#0072B2", ls="None", label="DeltaDTM v1.1.1"),
            Line2D([], [], marker="s", color="#D55E00", ls="None", label="National/local DTM"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=False,
        fontsize=6.8,
    )
    fig.text(0.5, 0.012, "Native vertical datums are not harmonized; differences combine elevation-product, datum and provider-resampling effects.", ha="center", va="bottom", fontsize=7.0, color="#4B5563")
    fig.subplots_adjust(left=0.13, right=0.975, top=0.91, bottom=0.10)
    save(fig, "FigS4_elevation_product_datum_sensitivity")


def supplementary_gallery() -> None:
    style()
    primary = pd.read_csv(PRIMARY)
    ids = [
        "lowestoft-p024-uk",
        "newport-p057-uk",
        "saint-nazaire",
        "delfzijl-del-nl",
        "sheerness-p015-uk",
        "hoekvanholla-hvh-nl",
        "denhelder-hel-nl",
        "immingham-p026-uk",
        "newlyn-p001-uk",
    ]
    rows = primary.set_index("station_id").loc[ids].reset_index()
    fig, axes = plt.subplots(3, 3, figsize=(7.2, 7.4))
    for i, (ax, (_, row)) in enumerate(zip(axes.flat, rows.iterrows())):
        classes, bbox, _ = station_layers(row)
        cmap = ListedColormap([CLASS_COLORS[x] for x in ["other_land", "unconnected", "connected", "tidal_water", "other_water", "excluded"]])
        ax.imshow(classes, cmap=cmap, vmin=0, vmax=5, origin="upper", extent=[bbox[0], bbox[2], bbox[1], bbox[3]], interpolation="nearest")
        ax.plot(row["lon"], row["lat"], marker="*", ms=6.5, color="#B22222", mec="white", mew=0.5)
        ax.set_title(f"{chr(97+i)}. {short_name(row['station'])}\nRP10 {row['coast_rp_rp10_m']:.2f} m; connected {row['connected_reference_land_pct']:.2f}%", loc="left", fontweight="bold", fontsize=7.5)
        ax.tick_params(labelsize=6.0)
    fig.legend(
        handles=[
            Patch(facecolor=CLASS_COLORS["tidal_water"], label="Ocean-connected water seed"),
            Patch(facecolor=CLASS_COLORS["connected"], label="Connected land below 2 m"),
            Patch(facecolor=CLASS_COLORS["unconnected"], label="Unconnected land below 2 m"),
            Patch(facecolor=CLASS_COLORS["other_land"], label="Other represented land"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=False,
        fontsize=6.7,
    )
    fig.subplots_adjust(left=0.08, right=0.985, top=0.92, bottom=0.06, hspace=0.32, wspace=0.23)
    save(fig, "FigS3_connectivity_gallery")


def supplementary_tidal_audit() -> None:
    style()
    frame = pd.read_csv(FIG_SOURCE / "FigS1_tidal_source_audit.csv")
    diagnostics = pd.read_csv(FIG_SOURCE / "Tidal_covariation_diagnostics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"wspace": 0.33})

    ax = axes[0]
    ax.scatter(frame["spring_tidal_range_m"], frame["coast_rp_rp10_m"], color="#0072B2", s=29, edgecolor="white", linewidth=0.5)
    rho = diagnostics.loc[diagnostics["relationship"].eq("storm_tide_vs_spring_tidal_range"), "spearman"].iloc[0]
    ax.text(0.04, 0.95, f"n={len(frame)}; Spearman ρ={rho:.2f}", transform=ax.transAxes, ha="left", va="top", fontsize=6.8)
    ax.set_xlabel("Source-verified mean spring tidal range (m)")
    ax.set_ylabel("COAST-RP 10-year storm tide (m)")
    ax.set_title("Tidal range covaries with storm-tide magnitude", loc="left", fontweight="bold")
    ax.grid(True, color="#D1D5DB", lw=0.45)
    repelled_station_labels(ax, frame, "spring_tidal_range_m", "coast_rp_rp10_m")
    panel(ax, "a")

    ax = axes[1]
    ax.scatter(frame["spring_tidal_range_m"], frame["connected_reference_land_pct"], color="#E69F00", s=29, edgecolor="white", linewidth=0.5)
    relationship = diagnostics.loc[diagnostics["relationship"].eq("connected_reference_land_pct_vs_spring_tidal_range"), "spearman"].iloc[0]
    ax.text(0.04, 0.95, f"n={len(frame)}; Spearman ρ={relationship:.2f}", transform=ax.transAxes, ha="left", va="top", fontsize=6.8)
    ax.set_yscale("log")
    ax.set_xlabel("Source-verified mean spring tidal range (m)")
    ax.set_ylabel("Connected share of represented land (%)")
    ax.set_title("Terrain susceptibility is not a tidal-range proxy", loc="left", fontweight="bold")
    ax.grid(True, color="#D1D5DB", lw=0.45)
    repelled_station_labels(ax, frame, "spring_tidal_range_m", "connected_reference_land_pct")
    panel(ax, "b")
    fig.subplots_adjust(left=0.09, right=0.985, top=0.91, bottom=0.17)
    save(fig, "FigS1_water_level_definition")


def supplementary_match_audit() -> None:
    style()
    frame = pd.read_csv(FIG_SOURCE / "Match_distance_audit_74stations.csv")
    hist = pd.read_csv(FIG_SOURCE / "Match_distance_histogram_source.csv")
    fig = plt.figure(figsize=(7.2, 3.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[0.9, 1.35], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    ax.bar(hist["bin_left_km"], hist["count"], width=0.46, align="edge", color="#4C78A8")
    ax.axvline(6.0, color="#D55E00", ls="--", lw=1.2, label="6 km screen")
    ax.set_xlim(0, max(10, float(frame["match_dist_km"].max()) + 1))
    ax.set_xlabel("Nearest COAST-RP distance (km)")
    ax.set_ylabel("Number of candidate stations")
    ax.set_title("Nearest-point extraction distances", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=6.5)
    ax.grid(axis="y", color="#D1D5DB", lw=0.45)
    panel(ax, "a")

    ax = fig.add_subplot(gs[0, 1])
    draw_tile_basemap(ax, (-10.0, 10.0, 46.5, 61.5), zoom=5)
    for _, row in frame.iterrows():
        x0, y0 = lonlat_to_mercator(float(row["lon"]), float(row["lat"]))
        x1, y1 = lonlat_to_mercator(float(row["coast_rp_source_lon"]), float(row["coast_rp_source_lat"]))
        included = bool(row["included_in_primary_match_sample"])
        color = "#4C78A8" if included else "#D55E00"
        ax.plot([x0, x1], [y0, y1], color=color, lw=0.45, alpha=0.70, zorder=5)
        ax.plot(x0, y0, marker="o", ms=2.8, color=color, mec="white", mew=0.25, zorder=6)
        ax.plot(x1, y1, marker="x", ms=2.8, color="#111111", mew=0.45, zorder=6)
    format_mercator_axes(ax, [-8, -4, 0, 4, 8], [48, 52, 56, 60])
    ax.set_title("Gauge-to-product pair audit", loc="left", fontweight="bold")
    ax.legend(
        handles=[
            Line2D([], [], marker="o", color="#4C78A8", ls="None", label="Included (n=68)"),
            Line2D([], [], marker="o", color="#D55E00", ls="None", label="Excluded (n=6)"),
            Line2D([], [], marker="x", color="#111111", ls="None", label="Matched COAST-RP point"),
        ],
        loc="lower left",
        frameon=True,
        fontsize=6.2,
    )
    panel(ax, "b")
    fig.subplots_adjust(left=0.08, right=0.985, top=0.91, bottom=0.16)
    save(fig, "FigS5_coastrp_match_audit")


def main() -> int:
    figure1()
    figure2()
    figure3()
    figure4()
    supplementary_local_dtm()
    supplementary_tidal_audit()
    supplementary_gallery()
    supplementary_match_audit()
    print("Wrote Figures 1-4 and supplementary diagnostic figures from frozen major-revision sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

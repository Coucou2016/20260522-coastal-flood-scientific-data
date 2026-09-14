from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)


def load_json(name: str):
    with (PROCESSED / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_station_overview() -> None:
    rp = pd.DataFrame(load_json("rp_comparison.json"))
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=220)

    ax.set_facecolor("#f8fafc")
    ax.axhspan(-60, 75, color="#f8fafc")
    ax.scatter(rp["coast_rp_rp10_m"], rp["gssr_rp10_m"], alpha=0)

    # Coarse regional rectangles provide geographic context without requiring
    # external map assets.
    regions = [
        (-130, 25, 60, 25, "North America"),
        (-15, 45, 25, 16, "NW Europe"),
        (95, 8, 35, 20, "East Asia"),
    ]
    for x, y, w, h, label in regions:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#e2e8f0", edgecolor="#94a3b8", lw=0.8))
        ax.text(x + w / 2, y + h + 1.5, label, ha="center", va="bottom", fontsize=8, color="#475569")

    colors = {"UK": "#2563eb", "Netherlands": "#0f766e", "France": "#9333ea", "USA": "#dc2626", "China": "#ea580c"}
    station_country = {
        "sheerness-p015-uk": "UK",
        "newlyn-p001-uk": "UK",
        "aberdeen-p038-uk": "UK",
        "hoekvanholla-hvh-nl": "Netherlands",
        "brest-france": "France",
        "newyork-the-battery": "USA",
        "charleston-sc": "USA",
        "hong-kong-b": "China",
    }
    coords = {
        "sheerness-p015-uk": (0.74306, 51.442),
        "newlyn-p001-uk": (-5.5417, 50.102),
        "aberdeen-p038-uk": (-2.0745, 57.143),
        "hoekvanholla-hvh-nl": (4.12, 51.977),
        "brest-france": (-4.5, 48.383),
        "newyork-the-battery": (-74.0142, 40.7006),
        "charleston-sc": (-79.9236, 32.7817),
        "hong-kong-b": (114.174, 22.302),
    }
    for sid, (lon, lat) in coords.items():
        row = rp.loc[rp["station_id"] == sid].iloc[0]
        c = colors[station_country[sid]]
        ax.scatter(lon, lat, s=45 + 45 * row["coast_rp_rp10_m"], color=c, edgecolor="white", lw=0.8, zorder=4)
        ax.text(lon + 2, lat + 0.7, sid.split("-")[0].title(), fontsize=7.5, color="#0f172a")

    ax.set_xlim(-135, 125)
    ax.set_ylim(15, 62)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Combo 1 tide-gauge sites and nearest COAST-RP coastal return levels", loc="left", fontsize=12, weight="bold")
    ax.text(0.01, 0.02, "Symbol size is proportional to COAST-RP RP10. Background regions are schematic.", transform=ax.transAxes, fontsize=8, color="#475569")
    ax.grid(color="#cbd5e1", lw=0.45, alpha=0.7)
    fig.tight_layout()
    fig.savefig(FIGURES / "combo1_station_overview_map.png", bbox_inches="tight")
    plt.close(fig)


def plot_inundation_comparison() -> None:
    records = load_json("inundation_sensitivity_all.json")
    df = pd.DataFrame(
        {
            "station": [r["station_name"] for r in records],
            "+0.5 m": [100 * r["flooded_fraction"]["0.5"] for r in records],
            "+1.0 m": [100 * r["flooded_fraction"]["1.0"] for r in records],
            "+2.0 m": [100 * r["flooded_fraction"]["2.0"] for r in records],
            "median_elev": [r["dem_stats"]["elev_median_m"] for r in records],
        }
    ).sort_values("+2.0 m", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=220)
    x = range(len(df))
    width = 0.23
    palette = ["#93c5fd", "#3b82f6", "#1e3a8a"]
    for i, col in enumerate(["+0.5 m", "+1.0 m", "+2.0 m"]):
        ax.bar([v + (i - 1) * width for v in x], df[col], width=width, label=col, color=palette[i], edgecolor="white")

    ax2 = ax.twinx()
    ax2.plot(list(x), df["median_elev"], color="#b45309", marker="o", lw=1.8, label="Median DEM elevation")
    ax2.set_ylabel("Median DeltaDTM elevation (m, EGM2008)", color="#92400e")
    ax2.tick_params(axis="y", labelcolor="#92400e")

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["station"], rotation=18, ha="right")
    ax.set_ylabel("Flooded fraction of coastal lowland cells (%)")
    ax.set_title("DeltaDTM static sea-level-rise sensitivity across European sites", loc="left", fontsize=12, weight="bold")
    ax.grid(axis="y", color="#cbd5e1", lw=0.45, alpha=0.7)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "combo1_inundation_multisite_summary.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    plot_station_overview()
    plot_inundation_comparison()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate Combo 1 QC figures (RP comparison, hydrograph, validation)."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from combo1_utils import FIGURES, PROCESSED, ensure_dirs


def fig_rp_comparison(rp_path: Path, out: Path) -> None:
    df = pd.read_parquet(rp_path)
    x = range(len(df))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - width / 2 for i in x], df["gssr_rp10_m"], width, label="GSSR RP10 (skew surge)")
    ax.bar([i + width / 2 for i in x], df["coast_rp_rp10_m"], width, label="COAST-RP RP10 (storm tide)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["station_id"], rotation=45, ha="right")
    ax.set_ylabel("Return level (m)")
    ax.set_title("GSSR vs COAST-RP — 10-year return level (different physical quantities)")
    ax.text(
        0.01,
        0.02,
        "EU/UK negative bias is expected (storm tide includes astronomical tide). "
        "US stations often agree within ~0.5 m.",
        transform=ax.transAxes,
        fontsize=7,
        color="0.4",
        va="bottom",
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def fig_rp_dual_panel(rp_path: Path, out: Path) -> None:
    """Split EU vs US to show product mismatch vs partial agreement."""
    df = pd.read_parquet(rp_path)
    eu_ids = {
        "sheerness-p015-uk",
        "newlyn-p001-uk",
        "aberdeen-p038-uk",
        "hoekvanholla-hvh-nl",
        "brest-france",
    }
    eu = df[df["station_id"].isin(eu_ids)]
    us = df[~df["station_id"].isin(eu_ids)]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, sub, title in (
        (axes[0], eu, "North Sea / NE Atlantic (large definition gap)"),
        (axes[1], us, "US + Hong Kong (closer magnitudes)"),
    ):
        if sub.empty:
            continue
        x = range(len(sub))
        w = 0.35
        ax.bar([i - w / 2 for i in x], sub["gssr_rp10_m"], w, label="GSSR skew-surge RP10")
        ax.bar([i + w / 2 for i in x], sub["coast_rp_rp10_m"], w, label="COAST-RP storm-tide RP10")
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub["station_id"], rotation=35, ha="right", fontsize=8)
        ax.set_title(title, fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        for i, row in sub.iterrows():
            ax.text(
                list(x)[list(sub.index).index(i)],
                max(row["gssr_rp10_m"], row["coast_rp_rp10_m"]) + 0.1,
                f"{row['rp10_bias_m']:+.2f} m",
                ha="center",
                fontsize=7,
                color="0.45",
            )
    axes[0].set_ylabel("Return level (m)")
    axes[0].legend(fontsize=8)
    fig.suptitle("RP10 comparison by region — do not force single-scale validation", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def fig_hydrograph(gssr_path: Path, rp_path: Path, station_id: str, out: Path) -> None:
    df = pd.read_parquet(gssr_path)
    sub = df[df["station_id"] == station_id].sort_values("date")
    rp = pd.read_parquet(rp_path)
    rp_row = rp[rp["station_id"] == station_id].iloc[0]

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(sub["date"], sub["surge_m"], lw=0.5, color="steelblue", label="GSSR daily max skew surge")
    p99 = sub["surge_m"].quantile(0.99)
    ax.axhline(p99, color="darkorange", ls="--", lw=1, label=f"99th pct ({p99:.2f} m)")
    ax.axhline(
        rp_row["gssr_rp10_m"],
        color="crimson",
        ls="-.",
        lw=1,
        label=f"GSSR empirical RP10 ({rp_row['gssr_rp10_m']:.2f} m)",
    )
    ax.axhline(
        rp_row["coast_rp_rp10_m"],
        color="purple",
        ls=":",
        lw=1.2,
        label=f"COAST-RP storm-tide RP10 @ coast ({rp_row['coast_rp_rp10_m']:.2f} m)",
    )
    ax.set_title(
        f"GSSR skew surge — {station_id}\n"
        f"(COAST-RP line is storm tide at nearest coast point, {rp_row['match_dist_km']:.1f} km away)"
    )
    ax.set_ylabel("Skew surge (m)")
    ax.set_xlabel("Date")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def fig_rp_multi(rp_path: Path, out: Path) -> None:
    df = pd.read_parquet(rp_path)
    rps = [10, 50, 100]
    x = range(len(df))
    n = len(rps)
    width = 0.12
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, rp in enumerate(rps):
        gcol, ccol = f"gssr_rp{rp}_m", f"coast_rp_rp{rp}_m"
        if gcol not in df.columns or ccol not in df.columns:
            continue
        offset = (i - (n - 1) / 2) * width
        ax.bar([xi + offset for xi in x], df[gcol], width, label=f"GSSR RP{rp}", alpha=0.85)
        ax.bar(
            [xi + offset + width for xi in x],
            df[ccol],
            width,
            label=f"COAST-RP RP{rp}",
            alpha=0.55,
            hatch="//",
        )
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["station_id"], rotation=45, ha="right")
    ax.set_ylabel("Return level (m)")
    ax.set_title("GSSR (skew surge) vs COAST-RP (storm tide) — RP10/50/100")
    ax.legend(ncol=3, fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def fig_driver_heatmap(corr_path: Path, out: Path) -> None:
    df = pd.read_parquet(corr_path)
    drivers = [
        ("spearman_surge_vs_pressure", "Pressure"),
        ("spearman_surge_vs_wind", "Wind"),
        ("spearman_surge_vs_precip", "Precip"),
    ]
    cols = [c for c, _ in drivers if c in df.columns]
    labels = [lab for c, lab in drivers if c in df.columns]
    if not cols:
        return
    mat = df.set_index("station_id")[cols].values
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["station_id"].values, fontsize=8)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Spearman: GSSR daily surge vs Open-Meteo ERA5 drivers (1980–2010)")
    fig.colorbar(im, ax=ax, label="ρ")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def fig_annual_max_validation(gssr_path: Path, rp_path: Path, out: Path) -> None:
    """Scatter GSSR annual max vs COAST-RP RP levels (shows definition gap, not bug)."""
    from combo1_utils import CONFIG, load_config, read_gssr_station

    cfg = load_config(CONFIG)
    rp = pd.read_parquet(rp_path)
    annual_max = []
    for st in cfg["stations"]:
        g = read_gssr_station(st)
        am = g.groupby(g["date"].dt.year)["surge_m"].max().mean()
        annual_max.append({"station_id": st["id"], "gssr_mean_annual_max_m": am})
    am_df = pd.DataFrame(annual_max)
    merged = rp.merge(am_df, on="station_id")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        merged["gssr_mean_annual_max_m"],
        merged["coast_rp_rp10_m"],
        s=60,
        c="steelblue",
        edgecolors="k",
        linewidths=0.4,
    )
    for _, row in merged.iterrows():
        ax.annotate(row["station_id"].split("-")[0], (row["gssr_mean_annual_max_m"], row["coast_rp_rp10_m"]), fontsize=7)
    lim = max(merged["coast_rp_rp10_m"].max(), merged["gssr_mean_annual_max_m"].max()) * 1.1
    ax.plot([0, lim], [0, lim], "k--", alpha=0.3, label="1:1 (not expected)")
    ax.set_xlabel("GSSR mean annual max skew surge (m)")
    ax.set_ylabel("COAST-RP RP10 storm tide (m)")
    ax.set_title("Cross-product check: mean annual max vs RP10 storm tide")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"figure -> {out}")


def main() -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    ensure_dirs()
    rp_path = PROCESSED / "rp_comparison.parquet"
    gssr_path = PROCESSED / "gssr_daily_merged.parquet"
    corr_path = PROCESSED / "driver_surge_correlations.parquet"
    if rp_path.exists():
        fig_rp_comparison(rp_path, FIGURES / "combo1_rp10_comparison.png")
        fig_rp_dual_panel(rp_path, FIGURES / "combo1_rp10_dual_region.png")
        fig_rp_multi(rp_path, FIGURES / "combo1_rp_multi_station.png")
        if gssr_path.exists():
            fig_annual_max_validation(gssr_path, rp_path, FIGURES / "combo1_gssr_coastrp_validation.png")
    if gssr_path.exists() and rp_path.exists():
        fig_hydrograph(gssr_path, rp_path, "sheerness-p015-uk", FIGURES / "combo1_hydrograph_sheerness.png")
    if corr_path.exists():
        fig_driver_heatmap(corr_path, FIGURES / "combo1_driver_correlation_heatmap.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

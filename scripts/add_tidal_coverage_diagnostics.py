#!/usr/bin/env python3
"""Summarize source-tracked tidal metadata coverage and diagnostic correlations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "figure_source"

EXTENDED_PATH = SOURCE_DIR / "Fig5_nw_europe_extended_screening.csv"
TIDE_PATH = SOURCE_DIR / "TableS_tidal_regime_metadata_source_tracked.csv"
JOINED_OUT = SOURCE_DIR / "Fig5_tidal_metadata_joined_diagnostics.csv"
COVERAGE_OUT = SOURCE_DIR / "Fig5_tidal_metadata_coverage_summary.csv"
CORR_OUT = SOURCE_DIR / "Fig5_tidal_available_rank_correlations.csv"


def corr(frame: pd.DataFrame, x: str, y: str, method: str) -> float | None:
    pair = frame[[x, y]].dropna()
    if len(pair) < 3:
        return None
    value = pair[x].corr(pair[y], method=method)
    if pd.isna(value):
        return None
    return float(value)


def top_set_mismatch(frame: pd.DataFrame, water_col: str, terrain_col: str) -> tuple[int, int, float | None]:
    if frame.empty:
        return 0, 0, None
    top_n = max(1, round(len(frame) * 0.2))
    top_water = set(frame.sort_values(water_col, ascending=False).head(top_n)["station_id"])
    top_terrain = set(frame.sort_values(terrain_col, ascending=False).head(top_n)["station_id"])
    overlap = len(top_water & top_terrain)
    mismatch = 1.0 - overlap / top_n
    return top_n, overlap, mismatch


def add_summary(rows: list[dict[str, object]], name: str, frame: pd.DataFrame) -> None:
    top_n, overlap, mismatch = top_set_mismatch(frame, "coast_rp_rp10_m", "connected_2m_lowland_pct")
    rows.append(
        {
            "subset": name,
            "n_sites": int(len(frame)),
            "n_tidal_values": int(frame["spring_tidal_range_m"].notna().sum()),
            "spearman_tidal_range_vs_D10": corr(frame, "spring_tidal_range_m", "D10_m", "spearman"),
            "spearman_tidal_range_vs_connected_2m": corr(
                frame,
                "spring_tidal_range_m",
                "connected_2m_lowland_pct",
                "spearman",
            ),
            "spearman_D10_vs_connected_2m": corr(frame, "D10_m", "connected_2m_lowland_pct", "spearman"),
            "kendall_D10_vs_connected_2m": corr(frame, "D10_m", "connected_2m_lowland_pct", "kendall"),
            "spearman_COAST_RP10_vs_connected_2m": corr(
                frame,
                "coast_rp_rp10_m",
                "connected_2m_lowland_pct",
                "spearman",
            ),
            "top20_n": top_n,
            "top20_overlap_COAST_vs_connected": overlap,
            "top20_mismatch_COAST_vs_connected": mismatch,
        }
    )


def main() -> int:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    extended = pd.read_csv(EXTENDED_PATH)
    tide = pd.read_csv(TIDE_PATH)

    joined = extended.merge(
        tide[
            [
                "station_id",
                "spring_tidal_range_m",
                "tidal_regime",
                "source_status",
                "tidal_range_metric",
                "source",
                "source_url",
            ]
        ],
        on="station_id",
        how="left",
    )
    joined["source_status"] = joined["source_status"].fillna("missing_or_not_yet_extracted")
    joined.to_csv(JOINED_OUT, index=False)

    counts = joined.groupby("source_status", dropna=False).size().reset_index(name="n_sites")
    counts["share_of_30_sites"] = counts["n_sites"] / len(joined)
    counts.to_csv(COVERAGE_OUT, index=False)

    source_verified = joined[joined["source_status"].eq("source_verified")].copy()
    available = joined[joined["spring_tidal_range_m"].notna()].copy()
    rows: list[dict[str, object]] = []
    add_summary(rows, "all_30_sites_rank_mismatch", joined)
    add_summary(rows, "source_verified_tidal_range_subset", source_verified)
    add_summary(rows, "all_available_tidal_range_subset", available)
    summary = pd.DataFrame(rows)
    summary.to_csv(CORR_OUT, index=False)

    print("Tidal metadata coverage")
    print(counts.to_string(index=False))
    print("\nTidal diagnostic correlations")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One-screen Combo 1 progress dashboard from summary JSON, logs, and raw data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from combo1_utils import CONFIG, FIGURES, LOGS, PROCESSED, RAW, load_config

ROOT = Path(__file__).resolve().parents[1]

PHASES = [
    ("P0 环境", "requirements.txt", None),
    ("P1 原始数据", "data/raw/coast_rp/extracted/COAST-RP.nc", "coast_rp"),
    ("P1 GSSR", "data/raw/gssr/era5", "gssr"),
    ("P1 Open-Meteo", "data/raw/open_meteo/hourly", "open_meteo"),
    ("P1 DeltaDTM索引", "data/raw/deltadtm/index/deltadtm_tiles.gpkg", "deltadtm_index"),
    ("P2 站匹配", "data/processed/coast_rp_nearest.parquet", "match"),
    ("P2 潮位合并", "data/processed/gssr_daily_merged.parquet", "gssr_merge"),
    ("P2 驱动相关", "data/processed/driver_surge_correlations.parquet", "drivers"),
    ("P3 淹没敏感性", "data/processed/inundation_sensitivity.json", "inundation"),
    ("P3 图表", "figures/combo1_rp10_comparison.png", "figures"),
]


def icon(ok: bool) -> str:
    return "OK " if ok else "-- "


def count_open_meteo() -> int:
    d = RAW / "open_meteo" / "hourly"
    return len(list(d.glob("*.json"))) if d.exists() else 0


def count_gssr_archives() -> int:
    d = RAW / "gssr" / "era5"
    return len(list(d.glob("*.7z"))) if d.exists() else 0


def count_deltadtm_tiles() -> int:
    d = RAW / "deltadtm" / "tiles"
    return len(list(d.rglob("*.tif"))) if d.exists() else 0


def load_summary() -> dict | None:
    p = PROCESSED / "combo1_summary.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def latest_log() -> Path | None:
    logs = sorted(LOGS.glob("combo1-run-*.md"), reverse=True)
    return logs[0] if logs else None


def inundation_dem_source() -> str:
    p = PROCESSED / "inundation_sensitivity.json"
    if not p.exists():
        return "n/a"
    data = json.loads(p.read_text(encoding="utf-8"))
    return str(data.get("dem_source", "n/a"))


def estimate_pct() -> int:
    weights = {
        "coast_rp": 12,
        "gssr": 12,
        "open_meteo": 12,
        "deltadtm_index": 8,
        "match": 12,
        "gssr_merge": 12,
        "drivers": 12,
        "inundation": 10,
        "figures": 10,
    }
    score = 0
    total = sum(weights.values())
    if (RAW / "coast_rp" / "extracted" / "COAST-RP.nc").exists():
        score += weights["coast_rp"]
    cfg = load_config()
    if count_gssr_archives() >= len(cfg["stations"]):
        score += weights["gssr"]
    if count_open_meteo() >= len(cfg["stations"]):
        score += weights["open_meteo"]
    if (RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg").exists():
        score += weights["deltadtm_index"]
    for key, rel in (
        ("match", "coast_rp_nearest.parquet"),
        ("gssr_merge", "gssr_daily_merged.parquet"),
        ("drivers", "driver_surge_correlations.parquet"),
    ):
        if (PROCESSED / rel).exists():
            score += weights[key]
    if (PROCESSED / "inundation_sensitivity.json").exists():
        score += weights["inundation"]
        if "synthetic" in inundation_dem_source():
            score += int(weights["inundation"] * 0.3)  # partial credit
    if (FIGURES / "combo1_rp10_comparison.png").exists():
        score += weights["figures"]
    return min(100, int(100 * score / total))


def main() -> int:
    cfg = load_config()
    n_st = len(cfg["stations"])
    summary = load_summary()
    pct = estimate_pct()

    print("=" * 60)
    print("COMBO 1 STATUS")
    print(f"  workspace : {ROOT}")
    print(f"  time      : {datetime.now().isoformat(timespec='seconds')}")
    print(f"  progress  : ~{pct}% (MVP pipeline; real DTM adds ~5%)")
    print("=" * 60)

    print("\n[Phases]")
    for label, rel, _ in PHASES:
        p = ROOT / rel if rel else ROOT / "requirements.txt"
        ok = p.exists() if rel else True
        if rel and rel.endswith("era5"):
            ok = count_gssr_archives() >= n_st
        elif rel and "open_meteo" in rel:
            ok = count_open_meteo() >= n_st
        print(f"  {icon(ok)}{label}")

    print("\n[Raw counts]")
    print(f"  GSSR archives     : {count_gssr_archives()}/{n_st}")
    print(f"  Open-Meteo JSON   : {count_open_meteo()}/{n_st}")
    print(f"  DeltaDTM COG tiles: {count_deltadtm_tiles()} (Sheerness needs >=1)")

    dem = inundation_dem_source()
    print(f"\n[Inundation DEM] {dem}")
    if "synthetic" in dem:
        print("  -> Run: python scripts\\download_deltadtm_tiles.py --station-id sheerness-p015-uk --download")
        print("     Then: python scripts\\inundation_sensitivity.py --station-id sheerness-p015-uk")

    if summary:
        print("\n[Summary JSON]")
        print(f"  generated : {summary.get('generated_at', '?')}")
        rp = summary.get("rp_comparison", {})
        if rp:
            print(
                f"  RP10 bias : mean {rp.get('mean_rp10_bias_m', float('nan')):.2f} m "
                f"(n={rp.get('n_stations', '?')})"
            )
        figs = summary.get("figures", [])
        print(f"  figures   : {len(figs)}")

    log = latest_log()
    if log:
        print(f"\n[Latest log] {log.name}")
        tail = log.read_text(encoding="utf-8").strip().splitlines()[-6:]
        for line in tail:
            print(f"  {line}")

    print("\n[Re-run pipeline]")
    print("  python scripts\\run_combo1_pipeline.py")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

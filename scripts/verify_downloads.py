#!/usr/bin/env python3
"""Basic integrity checks for Combo 1 downloaded files."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "combo1_stations.yaml"
RAW = ROOT / "data" / "raw"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_exists(path: Path, label: str, errors: list[str]) -> bool:
    if path.exists() and path.stat().st_size > 0:
        print(f"OK  {label}: {path} ({path.stat().st_size:,} B)")
        return True
    errors.append(f"MISSING {label}: {path}")
    print(f"FAIL {label}: {path}")
    return False


def check_zip(path: Path, label: str, errors: list[str]) -> bool:
    if not path.exists():
        errors.append(f"MISSING zip {label}")
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        print(f"OK  {label}: {len(names)} entries")
        return True
    except zipfile.BadZipFile:
        errors.append(f"CORRUPT zip {label}: {path}")
        print(f"FAIL {label}: bad zip")
        return False


def check_json(path: Path, label: str, errors: list[str]) -> bool:
    if not path.exists():
        errors.append(f"MISSING json {label}")
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        hourly = data.get("data", {}).get("hourly", {})
        times = hourly.get("time", [])
        if len(times) < 24:
            errors.append(f"SHORT series {label}: {len(times)} hours")
            print(f"WARN {label}: only {len(times)} hourly steps")
        else:
            print(f"OK  {label}: {len(times)} hourly steps")
        return True
    except json.JSONDecodeError:
        errors.append(f"INVALID json {label}")
        print(f"FAIL {label}: invalid JSON")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any failure")
    args = parser.parse_args()

    cfg = load_config(args.config)
    errors: list[str] = []

    coast_zip = RAW / "coast_rp" / "COAST-RP.zip"
    check_zip(coast_zip, "COAST-RP.zip", errors)

    coast_nc = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
    if coast_nc.exists():
        check_exists(coast_nc, "COAST-RP.nc", errors)
    else:
        print("INFO COAST-RP.nc not extracted (run download_combo1.py --extract)")

    for st in cfg["stations"]:
        gssr_path = RAW / "gssr" / "era5" / st["gssr_archive"]
        check_exists(gssr_path, f"GSSR {st['id']}", errors)

    check_exists(RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg", "DeltaDTM tile index", errors)

    om_dir = RAW / "open_meteo" / "hourly"
    if om_dir.exists():
        jsons = list(om_dir.glob("*.json"))
        if not jsons:
            errors.append("No Open-Meteo JSON files")
            print("FAIL Open-Meteo: no files")
        else:
            for p in jsons[:3]:
                check_json(p, p.name, errors)
            print(f"INFO Open-Meteo files: {len(jsons)}")
    else:
        print("INFO Open-Meteo not downloaded yet")

    manifest = ROOT / "data" / "manifest.json"
    if manifest.exists():
        print(f"OK  manifest.json ({manifest.stat().st_size:,} B)")

    print("---")
    if errors:
        print(f"{len(errors)} issue(s):")
        for e in errors:
            print(" ", e)
        return 1 if args.strict else 0
    print("All required checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

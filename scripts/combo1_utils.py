"""Shared helpers for Combo 1 processing scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "combo1_stations.yaml"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"

RP_VARS = {
    1: "storm_tide_rp_0001",
    2: "storm_tide_rp_0002",
    5: "storm_tide_rp_0005",
    10: "storm_tide_rp_0010",
    25: "storm_tide_rp_0025",
    50: "storm_tide_rp_0050",
    100: "storm_tide_rp_0100",
    250: "storm_tide_rp_0250",
    500: "storm_tide_rp_0500",
    1000: "storm_tide_rp_1000",
}


def load_config(path: Path = CONFIG) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)


def extract_gssr_archive(archive: Path, out_dir: Path) -> Path | None:
    """Extract .7z via 7-Zip CLI (py7zr may fail on broken lzma builds)."""
    if out_dir.exists() and list(out_dir.glob("*.csv")):
        return next(out_dir.glob("*.csv"))
    out_dir.mkdir(parents=True, exist_ok=True)
    seven_z = Path(r"D:\Program Files\MATLAB\R2018a\bin\win64\7z.exe")
    if not seven_z.exists():
        for candidate in ("7z", "7z.exe"):
            found = subprocess.run(
                ["where", candidate],
                capture_output=True,
                text=True,
                check=False,
            )
            if found.returncode == 0:
                seven_z = Path(found.stdout.strip().splitlines()[0])
                break
    if seven_z.exists():
        subprocess.run(
            [str(seven_z), "x", str(archive), f"-o{out_dir}", "-y"],
            check=True,
            capture_output=True,
        )
    else:
        try:
            import py7zr

            with py7zr.SevenZipFile(archive, mode="r") as zf:
                zf.extractall(path=out_dir)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Cannot extract {archive}: install 7-Zip or fix py7zr/lzma ({exc})"
            ) from exc
    csvs = list(out_dir.glob("*.csv"))
    return csvs[0] if csvs else None


def read_gssr_station(station: dict) -> pd.DataFrame:
    archive = RAW / "gssr" / "era5" / station["gssr_archive"]
    stem = Path(station["gssr_archive"]).stem
    out_dir = RAW / "gssr" / "era5" / "extracted" / stem
    csv_path = extract_gssr_archive(archive, out_dir)
    if csv_path is None:
        raise FileNotFoundError(f"No CSV after extracting {archive}")
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    surge_col = "surge_reconsturcted" if "surge_reconsturcted" in df.columns else "surge"
    df = df.rename(columns={surge_col: "surge_m"})
    df["station_id"] = station["id"]
    return df[["station_id", "date", "surge_m"]]


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km (WGS84 degrees)."""
    import math

    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    dlat = p2 - p1
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {path}")

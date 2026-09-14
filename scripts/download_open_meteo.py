#!/usr/bin/env python3
"""
Fetch ERA5 reanalysis drivers from Open-Meteo Historical Weather API
for stations listed in config/combo1_stations.yaml.

No API key required. Respect rate limits (see guide).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "combo1_stations.yaml"
OUT_DIR = ROOT / "data" / "raw" / "open_meteo" / "hourly"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARS = [
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "temperature_2m",
]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_station(
    session: requests.Session,
    station: dict,
    start_date: str,
    end_date: str,
    model: str,
    timezone: str,
) -> dict:
    params = {
        "latitude": station["lat"],
        "longitude": station["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "models": model,
        "timezone": timezone,
    }
    resp = session.get(ARCHIVE_URL, params=params, timeout=120)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Open-Meteo ERA5 for Combo1 stations")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--start", help="YYYY-MM-DD (default: climatology_start from config)")
    parser.add_argument("--end", help="YYYY-MM-DD (default: climatology_end from config)")
    parser.add_argument("--mode", choices=["climatology", "event"], default="climatology")
    parser.add_argument("--station-id", action="append", help="Limit to one or more station ids")
    parser.add_argument("--sleep", type=float, default=5.0, help="Seconds between API calls")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    cfg = load_config(args.config)
    defaults = cfg.get("open_meteo_defaults", {})
    if args.mode == "event":
        start = args.start or defaults.get("event_start", "2013-12-01")
        end = args.end or defaults.get("event_end", "2014-02-28")
    else:
        start = args.start or defaults.get("climatology_start", "1980-01-01")
        end = args.end or defaults.get("climatology_end", "2010-12-31")

    model = cfg.get("meta", {}).get("open_meteo_model", "era5")
    timezone = cfg.get("meta", {}).get("timezone", "UTC")
    stations = cfg["stations"]
    if args.station_id:
        wanted = set(args.station_id)
        stations = [s for s in stations if s["id"] in wanted]
        if not stations:
            print("No matching stations", file=sys.stderr)
            return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "coastal-flood-combo1/1.0"
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))

    for st in stations:
        out_path = args.out_dir / f"{st['id']}_{start}_{end}_{model}.json"
        if out_path.exists():
            print(f"skip (exists): {out_path.name}")
            continue
        print(f"fetch: {st['id']} {start}..{end}")
        try:
            payload = fetch_station(session, st, start, end, model, timezone)
        except requests.HTTPError as exc:
            print(f"ERROR {st['id']}: {exc}", file=sys.stderr)
            if exc.response is not None:
                print(exc.response.text[:500], file=sys.stderr)
            continue
        meta = {
            "station_id": st["id"],
            "station_name": st["name"],
            "lat": st["lat"],
            "lon": st["lon"],
            "start_date": start,
            "end_date": end,
            "model": model,
            "api": ARCHIVE_URL,
        }
        out_path.write_text(
            json.dumps({"meta": meta, "data": payload}, indent=2),
            encoding="utf-8",
        )
        time.sleep(args.sleep)

    print(f"done -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

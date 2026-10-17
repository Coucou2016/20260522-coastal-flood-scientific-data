#!/usr/bin/env python3
"""
Download Combo 1 core datasets:
  - GSSR (ERA5 per-station archives from GitHub gh-pages)
  - COAST-RP (4TU zip)
  - DeltaDTM index (+ optional Europe.zip or MVP tiles via manifest)

Open-Meteo is handled by scripts/download_open_meteo.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "combo1_stations.yaml"
UPSTREAM_MANIFEST = ROOT / "data" / "upstream_raw_manifest.csv"

SOURCES = {
    "coast_rp_zip": (
        "https://data.4tu.nl/ndownloader/items/"
        "4e291b8f-a37e-4378-8ca6-954a44fdc8fb/versions/2"
    ),
    "gssr_era5_bulk": "https://ndownloader.figshare.com/files/25187327",  # eraFiveSurgeReconstruction.7z
    "gssr_github_base": "https://raw.githubusercontent.com/moinabyssinia/gssr/gh-pages/erafive/",
    "gssr_metadata_geojson": (
        "https://raw.githubusercontent.com/moinabyssinia/gssr/gh-pages/eraint.geojson"
    ),
    "deltadtm_tiles_gpkg": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "60a69899-2e67-4f9f-8761-3b57094acd12"
    ),
    "deltadtm_readme": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "71c77b5f-b340-4fdb-a1b1-1d255b8ddb0f"
    ),
    "deltadtm_europe_zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "cb0b8ee3-b018-4828-a74e-2fb05020b1b6"
    ),
}


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_sha256(dest: Path) -> str | None:
    if not UPSTREAM_MANIFEST.is_file():
        return None
    relative = dest.resolve().relative_to(ROOT.resolve()).as_posix()
    with UPSTREAM_MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["relative_path"].replace("\\", "/") == relative:
                return row["sha256"].lower()
    return None


def verify_sha256(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, found {actual}")


def download_url(url: str, dest: Path, chunk_mb: int = 8) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = expected_sha256(dest)
    if dest.exists() and dest.stat().st_size > 0:
        if expected is None:
            raise ValueError(f"Refusing to reuse unverified existing file absent from manifest: {dest}")
        verify_sha256(dest, expected)
        print(f"skip (verified SHA-256): {dest}")
        return
    print(f"download: {url}\n  -> {dest}")
    req = Request(url, headers={"User-Agent": "coastal-flood-combo1/1.0"})
    temporary = dest.with_suffix(dest.suffix + ".part")
    with urlopen(req, timeout=300) as resp, temporary.open("wb") as out:
        chunk = chunk_mb * 1024 * 1024
        while True:
            block = resp.read(chunk)
            if not block:
                break
            out.write(block)
    if expected is not None:
        verify_sha256(temporary, expected)
    temporary.replace(dest)
    status = "verified" if expected is not None else "downloaded (no manifest hash available)"
    print(f"saved {dest.stat().st_size:,} bytes; {status}")


def extract_zip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        root = out_dir.resolve()
        for member in zf.infolist():
            member_path = Path(member.filename.replace("\\", "/"))
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"unsafe ZIP member path: {member.filename!r}")
            target = (root / member_path).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"ZIP member escapes extraction root: {member.filename!r}")
            # Unix symlinks are encoded in the high 16 bits of external_attr.
            if ((member.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError(f"ZIP symlink member is not allowed: {member.filename!r}")
        zf.extractall(root)
    print(f"extracted -> {out_dir}")


def download_gssr_stations(cfg: dict, out_dir: Path) -> None:
    folder = cfg.get("meta", {}).get("gssr_github_folder", "erafive")
    base = SOURCES["gssr_github_base"]
    for st in cfg["stations"]:
        archive = st["gssr_archive"]
        url = f"{base}{archive}"
        dest = out_dir / archive
        download_url(url, dest)


def download_coast_rp(raw_dir: Path, extract: bool) -> None:
    zip_path = raw_dir / "coast_rp" / "COAST-RP.zip"
    download_url(SOURCES["coast_rp_zip"], zip_path)
    if extract:
        extract_zip(zip_path, raw_dir / "coast_rp" / "extracted")


def download_deltadtm_index(raw_dir: Path) -> None:
    idx = raw_dir / "deltadtm" / "index"
    download_url(SOURCES["deltadtm_tiles_gpkg"], idx / "deltadtm_tiles.gpkg")
    download_url(SOURCES["deltadtm_readme"], idx / "README.md")


def download_deltadtm_europe(raw_dir: Path, extract: bool) -> None:
    dest = raw_dir / "deltadtm" / "zips" / "Europe.zip"
    download_url(SOURCES["deltadtm_europe_zip"], dest)
    if extract:
        tiles = raw_dir / "deltadtm" / "tiles"
        extract_zip(dest, tiles)


def download_gssr_bulk(raw_dir: Path) -> None:
    dest = raw_dir / "gssr" / "era5" / "eraFiveSurgeReconstruction.7z"
    download_url(SOURCES["gssr_era5_bulk"], dest)
    print("Note: extract .7z with 7-Zip or py7zr; then unpack per-station CSVs.")


def run_open_meteo(mode: str) -> None:
    script = ROOT / "scripts" / "download_open_meteo.py"
    cmd = [sys.executable, str(script), "--mode", mode]
    print("run:", " ".join(cmd))
    subprocess.run(cmd, check=False)


def write_manifest(raw_dir: Path) -> None:
    manifest = {}
    for path in sorted(raw_dir.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(ROOT))] = path.stat().st_size
    out = ROOT / "data" / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Combo1 static datasets")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument(
        "--tier",
        choices=["mvp-min", "mvp-terrain", "full-gssr", "full-europe-dtm"],
        default="mvp-min",
        help="mvp-min: COAST-RP + GSSR stations + DTM index; mvp-terrain: + Europe.zip",
    )
    parser.add_argument("--extract", action="store_true", help="Unzip COAST-RP / Europe after download")
    parser.add_argument("--open-meteo", action="store_true", help="Also call download_open_meteo.py")
    parser.add_argument("--meteo-mode", choices=["climatology", "event"], default="climatology")
    parser.add_argument(
        "--tiles-station",
        metavar="STATION_ID",
        help="After index download, extract DeltaDTM tiles for station bbox (see download_deltadtm_tiles.py)",
    )
    parser.add_argument(
        "--tiles-download",
        action="store_true",
        help="With --tiles-station: download continent zip if needed (~2.4 GB for Europe)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    raw_dir = ROOT / "data" / "raw"

    # Always: small, fast
    download_coast_rp(raw_dir, extract=args.extract)
    download_gssr_stations(cfg, raw_dir / "gssr" / "era5")
    download_url(SOURCES["gssr_metadata_geojson"], raw_dir / "gssr" / "metadata" / "eraint.geojson")
    download_deltadtm_index(raw_dir)

    if args.tier in ("mvp-terrain", "full-europe-dtm"):
        download_deltadtm_europe(raw_dir, extract=args.extract)

    if args.tier == "full-gssr":
        download_gssr_bulk(raw_dir)

    if args.open_meteo:
        run_open_meteo(args.meteo_mode)

    if args.tiles_station:
        tile_script = ROOT / "scripts" / "download_deltadtm_tiles.py"
        cmd = [sys.executable, str(tile_script), "--station-id", args.tiles_station]
        if args.tiles_download:
            cmd.append("--download")
        print("run:", " ".join(cmd))
        subprocess.run(cmd, check=False)

    write_manifest(raw_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

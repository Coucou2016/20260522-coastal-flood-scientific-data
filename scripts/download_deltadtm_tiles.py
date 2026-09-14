#!/usr/bin/env python3
"""
Download / extract DeltaDTM COG tiles for a station bbox (Combo 1 MVP).

4TU distributes continent zips only (no per-tile HTTP). This script:
  1. Resolves intersecting tiles from deltadtm_tiles.gpkg
  2. Optionally downloads the smallest required continent zip (e.g. Europe.zip ~2.4 GB)
  3. Extracts only matching *.tif members into data/raw/deltadtm/tiles/
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
from shapely.geometry import box

from combo1_utils import CONFIG, RAW, load_config

ROOT = Path(__file__).resolve().parents[1]
TILE_INDEX = RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg"
TILES_DIR = RAW / "deltadtm" / "tiles"
ZIPS_DIR = RAW / "deltadtm" / "zips"

# Expected sizes (bytes) from 4TU v4 listing — used to detect aborted downloads.
CONTINENT_BYTES = {
    "Europe.zip": 2_386_070_935,
    "Africa.zip": 2_777_497_652,
    "Asia.zip": 17_279_481_550,
    "North_America.zip": 6_854_143_924,
    "Oceania.zip": 2_183_866_483,
    "South_America.zip": 4_023_320_187,
}

CONTINENT_URLS = {
    "Africa.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "22ffa027-184b-4f67-9979-c182f3dfb1ab"
    ),
    "Antarctica.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "ca957a40-34fa-41eb-b101-e45d1ccbd890"
    ),
    "Asia.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "672eba4c-1334-44c6-8119-8879ded25912"
    ),
    "Europe.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "cb0b8ee3-b018-4828-a74e-2fb05020b1b6"
    ),
    "North_America.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "037664c6-1494-4889-9689-a56570728320"
    ),
    "Oceania.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "de972de1-26bd-4303-afdf-21a90a232cff"
    ),
    "South_America.zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "db980f00-63cd-4a07-a4df-55ab06510594"
    ),
    "Seven_seas_(open_ocean).zip": (
        "https://data.4tu.nl/file/1da2e70f-6c4d-4b03-86bd-b53e789cc629/"
        "fe986ba6-3db9-40e2-8a49-0fcdb341244a"
    ),
}


def station_bbox(station: dict, buffer_deg: float = 0.05) -> tuple[float, float, float, float]:
    return (
        station["lon"] - buffer_deg,
        station["lat"] - buffer_deg,
        station["lon"] + buffer_deg,
        station["lat"] + buffer_deg,
    )


def tiles_for_bbox(bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(TILE_INDEX)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    region = gpd.GeoDataFrame(geometry=[box(*bbox)], crs=4326)
    return gdf[gdf.intersects(region.geometry.iloc[0])]


def existing_tile_paths(tile_names: list[str]) -> list[Path]:
    found: list[Path] = []
    if not TILES_DIR.exists():
        return found
    for name in tile_names:
        matches = list(TILES_DIR.rglob(f"*{name}*"))
        found.extend(matches)
    return found


def continent_name(path: Path) -> str:
    return path.name.removesuffix(".part")


def zip_complete(dest: Path) -> bool:
    expected = CONTINENT_BYTES.get(continent_name(dest))
    if not dest.exists():
        return False
    size = dest.stat().st_size
    if expected and size < expected * 0.99:
        return False
    if expected and size >= expected * 0.99:
        try:
            with zipfile.ZipFile(dest) as zf:
                zf.testzip()
            return True
        except zipfile.BadZipFile:
            print(f"corrupt zip: {dest}", flush=True)
            return False
    return size > 0


def part_path(dest: Path) -> Path:
    return dest.parent / f"{dest.name}.part"


def resolve_zip_path(dest: Path) -> Path | None:
    """Return a complete zip path (final or .part), or None if missing/incomplete."""
    if zip_complete(dest):
        return dest
    part = part_path(dest)
    if zip_complete(part):
        return part
    if dest.exists():
        expected = CONTINENT_BYTES.get(dest.name, 0)
        print(
            f"incomplete zip ({dest.stat().st_size:,} / {expected:,} B): {dest.name}",
            flush=True,
        )
    return None


def finalize_download(dest: Path, part: Path) -> bool:
    """Move completed .part to dest; tolerate locked incomplete dest."""
    if not zip_complete(part):
        return False
    try:
        if dest.exists() and not zip_complete(dest):
            dest.unlink()
    except OSError as exc:
        print(f"WARN: cannot remove locked {dest.name} ({exc}); using {part.name}", flush=True)
        return True
    try:
        part.replace(dest)
        print(f"installed {dest.name} ({dest.stat().st_size:,} B)", flush=True)
    except OSError:
        print(f"WARN: keep complete file at {part}", flush=True)
    return True


def download_url(url: str, dest: Path, chunk_mb: int = 8) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if zip_complete(dest):
        print(f"skip (complete): {dest} ({dest.stat().st_size:,} B)", flush=True)
        return
    part = part_path(dest)
    expected = CONTINENT_BYTES.get(dest.name, 0)
    resume_from = part.stat().st_size if part.exists() else 0
    if resume_from and expected and resume_from >= expected * 0.99:
        print(f"part file complete, finalizing: {part.name}", flush=True)
        finalize_download(dest, part)
        return

    headers = {"User-Agent": "coastal-flood-combo1/1.0"}
    mode = "ab" if resume_from else "wb"
    if resume_from:
        headers["Range"] = f"bytes={resume_from}-"
        print(f"resume download from {resume_from / 1e6:.0f} MB -> {part}", flush=True)
    else:
        print(f"download: {url}\n  -> {part}", flush=True)

    req = Request(url, headers=headers)
    with urlopen(req, timeout=600) as resp, part.open(mode) as out:
        if resume_from and resp.status not in (206, 200):
            print(f"WARN: resume got HTTP {resp.status}; restarting part file", flush=True)
            part.unlink()
            return download_url(url, dest, chunk_mb)
        chunk = chunk_mb * 1024 * 1024
        total = resume_from
        while True:
            block = resp.read(chunk)
            if not block:
                break
            out.write(block)
            total += len(block)
            if (total - resume_from) % (64 * 1024 * 1024) < chunk:
                print(f"  ... {total / 1e6:.0f} MB", flush=True)
    print(f"saved {part.stat().st_size:,} bytes", flush=True)
    finalize_download(dest, part)


def extract_tiles_from_zip(zip_path: Path, tile_names: list[str], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    stems = {Path(n).stem for n in tile_names}
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".tif")]
        for member in members:
            base = Path(member).name
            if not any(stem in base for stem in stems):
                continue
            target = out_dir / base
            if target.exists() and target.stat().st_size > 0:
                print(f"skip extract (exists): {target.name}")
                extracted.append(target)
                continue
            print(f"extract: {member}")
            zf.extract(member, out_dir)
            # zip may preserve subdirs; flatten to tiles/
            pulled = out_dir / member
            if pulled.exists() and pulled != target:
                target.parent.mkdir(parents=True, exist_ok=True)
                pulled.replace(target)
            extracted.append(target if target.exists() else out_dir / base)
    return extracted


def ensure_tiles_for_station(
    station_id: str,
    buffer_deg: float = 0.05,
    download: bool = False,
) -> dict:
    cfg = load_config()
    stations = [s for s in cfg["stations"] if s["id"] == station_id]
    if not stations:
        raise ValueError(f"Unknown station {station_id}")
    st = stations[0]
    bbox = station_bbox(st, buffer_deg)
    tiles = tiles_for_bbox(bbox)
    tile_names = [str(r["tile"]) for _, r in tiles.iterrows()]
    report = {
        "station_id": station_id,
        "bbox": bbox,
        "tile_names": tile_names,
        "zipfiles_needed": sorted({str(r["zipfile"]) for _, r in tiles.iterrows()}),
        "existing": [str(p) for p in existing_tile_paths(tile_names)],
        "extracted": [],
        "downloaded_zips": [],
    }

    if report["existing"]:
        print(f"tiles already present: {len(report['existing'])}")
        return report

    for zip_name in report["zipfiles_needed"]:
        zip_path = ZIPS_DIR / zip_name
        if download and resolve_zip_path(zip_path) is None:
            url = CONTINENT_URLS.get(zip_name)
            if not url:
                print(f"WARN: no URL for {zip_name}")
                continue
            download_url(url, zip_path)
            report["downloaded_zips"].append(str(zip_path))
        usable = resolve_zip_path(zip_path)
        if usable is None:
            print(f"MISSING or incomplete zip (use --download): {zip_path}")
            continue
        pulled = extract_tiles_from_zip(usable, tile_names, TILES_DIR)
        report["extracted"].extend(str(p) for p in pulled)

    report["existing"] = [str(p) for p in existing_tile_paths(tile_names)]
    return report


EU_STATION_IDS = [
    "sheerness-p015-uk",
    "newlyn-p001-uk",
    "aberdeen-p038-uk",
    "hoekvanholla-hvh-nl",
    "brest-france",
]

EUROPE_ZIP_MD5 = "ef5b07bcd3a068baab1207a90d051789"


def verify_zip_md5(path: Path) -> bool:
    import hashlib

    if not path.exists():
        return False
    expected = CONTINENT_BYTES.get(path.name)
    if expected and path.stat().st_size < expected * 0.99:
        print(f"size mismatch: {path.stat().st_size:,} < {expected:,}")
        return False
    if path.name != "Europe.zip":
        return True
    print(f"computing MD5 for {path.name} ...")
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    ok = h.hexdigest() == EUROPE_ZIP_MD5
    print(f"MD5 {h.hexdigest()} expected {EUROPE_ZIP_MD5} -> {'OK' if ok else 'FAIL'}")
    return ok


def extract_batch_eu(buffer_deg: float = 0.05, download: bool = False) -> dict:
    summary: dict = {"stations": {}, "all_tiles": set()}
    for sid in EU_STATION_IDS:
        rep = ensure_tiles_for_station(sid, buffer_deg, download)
        summary["stations"][sid] = rep
        summary["all_tiles"].update(rep.get("tile_names", []))
    summary["all_tiles"] = sorted(summary["all_tiles"])
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract DeltaDTM tiles for one station bbox")
    parser.add_argument("--station-id", default="sheerness-p015-uk")
    parser.add_argument("--buffer-deg", type=float, default=0.05)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download continent zip(s) if missing (~2.4 GB for Europe.zip)",
    )
    parser.add_argument("--batch-eu", action="store_true", help="Extract tiles for all EU MVP stations")
    parser.add_argument("--verify-zip", action="store_true", help="Verify Europe.zip MD5 before extract")
    parser.add_argument("--list-only", action="store_true", help="Print tile list and exit")
    args = parser.parse_args()

    if not TILE_INDEX.exists():
        print(f"Missing tile index: {TILE_INDEX}")
        print("Run: python scripts/download_combo1.py --tier mvp-min")
        return 1

    europe_zip = ZIPS_DIR / "Europe.zip"
    if args.verify_zip or args.batch_eu or args.download:
        if europe_zip.exists() and not verify_zip_md5(europe_zip):
            print("Europe.zip corrupt — delete and re-download with --download")
            if args.download:
                try:
                    europe_zip.unlink()
                except OSError as exc:
                    print(f"WARN: cannot delete {europe_zip}: {exc}")

    if args.batch_eu:
        if args.download and not verify_zip_md5(europe_zip):
            url = CONTINENT_URLS["Europe.zip"]
            download_url(url, europe_zip)
            if not verify_zip_md5(europe_zip):
                print("Europe.zip still invalid after download")
                return 1
        summary = extract_batch_eu(args.buffer_deg, download=False)
        n_ok = sum(1 for s in summary["stations"].values() if s["existing"])
        print(f"batch-eu: {n_ok}/{len(EU_STATION_IDS)} stations have tiles")
        print(f"tiles needed: {summary['all_tiles']}")
        return 0 if n_ok == len(EU_STATION_IDS) else 1

    cfg = load_config()
    st = next(s for s in cfg["stations"] if s["id"] == args.station_id)
    bbox = station_bbox(st, args.buffer_deg)
    tiles = tiles_for_bbox(bbox)
    print(f"Station {args.station_id} bbox {bbox}")
    print(tiles[["tile", "zipfile", "longitude", "latitude"]].to_string())

    if args.list_only:
        return 0

    if args.download and not verify_zip_md5(europe_zip):
        download_url(CONTINENT_URLS["Europe.zip"], europe_zip)

    report = ensure_tiles_for_station(args.station_id, args.buffer_deg, args.download)
    print("---")
    print(f"existing tiles: {len(report['existing'])}")
    print(f"newly extracted: {len(report['extracted'])}")
    return 0 if report["existing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Build a public, hash-addressed inventory of local upstream raw inputs."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CSV_OUT = ROOT / "data" / "upstream_raw_manifest.csv"
JSON_OUT = ROOT / "data" / "upstream_raw_manifest.json"

SOURCES = {
    "coast_rp": {
        "source": "https://doi.org/10.4121/13392314.v2",
        "note": "Upstream COAST-RP product; reacquire from the authoritative repository.",
    },
    "gssr": {
        "source": "https://doi.org/10.6084/m9.figshare.c.5124878",
        "note": "Upstream GSSR product; reacquire from the authoritative repository.",
    },
    "deltadtm": {
        "source": "https://doi.org/10.4121/21997565.v4",
        "note": "Upstream DeltaDTM product; local v1.1 files are not copied into Git.",
    },
    "open_meteo": {
        "source": "https://open-meteo.com/en/docs/historical-weather-api",
        "note": "Cached API response; reacquire under the provider's current terms.",
    },
    "local_dtm": {
        "source": "https://environment.data.gov.uk/ ; https://www.ahn.nl/",
        "note": "National/local elevation products; provider terms and native datums apply.",
    },
    "naturalearth": {
        "source": "https://www.naturalearthdata.com/",
        "note": "Natural Earth map context; public-domain upstream source.",
    },
    "map_tiles": {
        "source": "https://carto.com/attributions",
        "note": "Historical CARTO tile cache; not redistributed.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(f"Raw-data directory not found: {RAW}")

    rows: list[dict[str, object]] = []
    for path in sorted(item for item in RAW.rglob("*") if item.is_file()):
        relative = path.relative_to(ROOT).as_posix()
        dataset = path.relative_to(RAW).parts[0]
        metadata = SOURCES.get(
            dataset,
            {"source": "See project documentation", "note": "Upstream file; not redistributed."},
        )
        rows.append(
            {
                "relative_path": relative,
                "dataset": dataset,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "authoritative_source": metadata["source"],
                "redistribution_status": "not_committed_reacquire_from_upstream",
                "note": metadata["note"],
            }
        )

    fieldnames = list(rows[0]) if rows else []
    with CSV_OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "schema": "upstream-raw-input-manifest-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "hash_algorithm": "SHA-256",
        "policy": "Raw upstream files are not committed; reacquire from authoritative sources.",
        "datasets": SOURCES,
        "files": rows,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {CSV_OUT} and {JSON_OUT}: {len(rows)} files")


if __name__ == "__main__":
    main()


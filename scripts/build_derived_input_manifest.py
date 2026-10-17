#!/usr/bin/env python3
"""Write hashes for the compact inputs used by derived-mode reproduction."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "derived_input_manifest.json"
INPUTS = [
    "config/coastal_spatial_blocks_v2.csv",
    "data/figure_source/Fig5_station_candidate_audit.csv",
    "data/figure_source/Fig6_mask_aware_terrain_area_metrics.csv",
    "data/figure_source/Terrain_robustness_grid_74stations.csv",
    "data/figure_source/TableS_coastrp_multi_return_period_68stations.csv",
    "data/figure_source/TableS_tidal_regime_metadata_source_tracked.csv",
    "data/figure_source/TableS_local_dtm_product_datum_crosscheck.csv",
    "data/figure_source/Threshold_response_0_3m_68stations.csv",
    "data/figure_source/Threshold_integrated_terrain_metrics_68stations.csv",
    "data/figure_source/Threshold_integrated_associations.csv",
    "data/figure_source/Water_land_topology_sensitivity_68stations.csv",
    "data/figure_source/Water_land_topology_summary.csv",
    "data/figure_source/Coastline_oriented_window_68stations.csv",
    "data/figure_source/Coastline_window_sensitivity_summary.csv",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    missing = [relative for relative in INPUTS if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit("Missing derived inputs: " + ", ".join(missing))
    payload = {
        "schema": "coastal-screening-derived-inputs-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Checksummed derived station inputs; not an upstream raw-data manifest.",
        "files": [
            {
                "path": relative,
                "bytes": (ROOT / relative).stat().st_size,
                "sha256": sha256(ROOT / relative),
            }
            for relative in INPUTS
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

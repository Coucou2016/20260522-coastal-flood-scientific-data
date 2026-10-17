#!/usr/bin/env python3
"""Run either compact derived-input or complete upstream reproduction."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED_MANIFEST = ROOT / "data" / "derived_input_manifest.json"
UPSTREAM_MANIFEST = ROOT / "data" / "upstream_raw_manifest.csv"
RECEIPT = ROOT / "reproduction_receipt.json"


def runtime_record() -> dict[str, object]:
    packages = {}
    for name in ("numpy", "pandas", "scipy", "xarray", "netCDF4", "rasterio", "pyproj", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": packages,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_derived_inputs() -> int:
    if not DERIVED_MANIFEST.is_file():
        raise FileNotFoundError(f"Missing {DERIVED_MANIFEST}; run build_derived_input_manifest.py")
    manifest = json.loads(DERIVED_MANIFEST.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"Missing or size-mismatched derived input: {record['path']}")
        if sha256(path) != record["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for derived input: {record['path']}")
    return len(manifest["files"])


def verify_upstream_inputs() -> int:
    if not UPSTREAM_MANIFEST.is_file():
        raise FileNotFoundError(f"Missing upstream manifest: {UPSTREAM_MANIFEST}")
    verified = 0
    with UPSTREAM_MANIFEST.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            path = ROOT / record["relative_path"]
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing upstream file {record['relative_path']}; reacquire from {record['authoritative_source']}"
                )
            if path.stat().st_size != int(record["bytes"]) or sha256(path) != record["sha256"]:
                raise RuntimeError(f"Upstream file integrity mismatch: {record['relative_path']}")
            verified += 1
    return verified


def run_step(name: str, command: list[str], env: dict[str, str]) -> dict[str, object]:
    print(f"[reproduce] {name}", flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    return {"name": name, "command": command, "exit_code": completed.returncode}


def derived_steps() -> list[tuple[str, list[str]]]:
    return [
        ("derived terrain summaries", [sys.executable, "scripts/rebuild_frozen_primary_analysis.py", "--reuse-detail"]),
        ("derived spatial statistics", [sys.executable, "scripts/add_external_review_diagnostics.py", "--reuse-derived"]),
        ("decision-stability diagnostics", [sys.executable, "scripts/add_decision_instability_diagnostics.py"]),
        ("COAST-RP coordinate-match review", [sys.executable, "scripts/add_coastrp_same_coast_audit.py"]),
        ("derived-data figures", [sys.executable, "scripts/make_major_revision_figures.py", "--derived-only"]),
        ("standalone manuscript", [sys.executable, "scripts/build_standalone_paper.py"]),
        ("supplementary information", [sys.executable, "scripts/build_supplementary_information.py"]),
        ("research report", [sys.executable, "scripts/build_research_report_v2.py"]),
        ("internal consistency audit", [sys.executable, "scripts/build_scientific_integrity_review_v2.py"]),
        ("standalone HTML validation", [sys.executable, "scripts/validate_standalone_html.py", "paper.html", "supplementary_information.html", "report.html", "manuscript/internal_scientific_consistency_audit.html"]),
        ("scientific contracts", [sys.executable, "-m", "pytest", "tests"]),
    ]


def full_steps() -> list[tuple[str, list[str]]]:
    return [
        ("COAST-RP focal station matching", [sys.executable, "scripts/match_stations_to_coastrp.py"]),
        ("GSSR and COAST-RP station integration", [sys.executable, "scripts/merge_gssr_coastrp.py"]),
        ("focal return-level source table", [sys.executable, "-c", "import sys; sys.path.insert(0, 'scripts'); from make_cee_main_figures import load_rp; load_rp()"]),
        ("regional candidate construction", [sys.executable, "scripts/build_nw_europe_extended_diagnostics.py"]),
        ("return-level uncertainty diagnostics", [sys.executable, "scripts/add_uncertainty_diagnostics.py"]),
        ("regional terrain candidates", [sys.executable, "scripts/add_advanced_terrain_rank_diagnostics.py"]),
        ("official-mask terrain diagnostics", [sys.executable, "scripts/add_mask_aware_terrain_diagnostics.py"]),
        ("frozen primary analysis", [sys.executable, "scripts/rebuild_frozen_primary_analysis.py"]),
        ("threshold-integrated terrain diagnostics", [sys.executable, "scripts/add_threshold_integrated_terrain_metric.py"]),
        ("water/land topology diagnostics", [sys.executable, "scripts/add_water_land_topology_sensitivity.py"]),
        ("coastline-oriented-window diagnostics", [sys.executable, "scripts/add_coastline_window_sensitivity.py"]),
        ("spatial diagnostics", [sys.executable, "scripts/add_external_review_diagnostics.py"]),
        ("decision-stability diagnostics", [sys.executable, "scripts/add_decision_instability_diagnostics.py"]),
        ("COAST-RP coordinate-match review", [sys.executable, "scripts/add_coastrp_same_coast_audit.py"]),
        ("local-DTM product/datum cross-check", [sys.executable, "scripts/add_local_dtm_validation.py"]),
        ("all figures", [sys.executable, "scripts/make_major_revision_figures.py"]),
        *derived_steps()[5:],
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("derived", "full"))
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the selected input manifest without executing the workflow.",
    )
    args = parser.parse_args()
    verified = verify_derived_inputs() if args.mode == "derived" else verify_upstream_inputs()
    if args.verify_only:
        print(f"Verified {verified} input files for {args.mode} mode.")
        return 0
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    receipt = {
        "schema": "coastal-screening-reproduction-receipt-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "verified_input_files": verified,
        "input_scope": "checksummed derived inputs" if args.mode == "derived" else "upstream raw files",
        "runtime": runtime_record(),
        "status": "RUNNING",
        "steps": [],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    try:
        for name, command in (derived_steps() if args.mode == "derived" else full_steps()):
            receipt["active_step"] = name
            RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            receipt["steps"].append(run_step(name, command, env))
        receipt["status"] = "PASS"
        receipt.pop("active_step", None)
    except BaseException as error:
        receipt["status"] = "FAILED"
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {RECEIPT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

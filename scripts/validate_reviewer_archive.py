#!/usr/bin/env python3
"""Extract the reviewer ZIP and run its derived reproduction in isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "major_revision_reviewer_package.zip"

DETERMINISTIC_OUTPUTS = [
    "data/figure_source/Primary_terrain_components_68stations.csv",
    "data/figure_source/Return_period_sensitivity.csv",
    "data/figure_source/Spatial_block_bootstrap_intervals.csv",
    "data/figure_source/Topk_spatial_null_curves.csv",
    "data/figure_source/Decision_instability_station_metrics.csv",
    "data/figure_source/COAST_RP_same_coast_match_audit.csv",
    "manuscript/process_terrain_coastal_flood_CEE_manuscript.md",
    "supplementary_information.md",
    "report.md",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument(
        "--reuse-current-environment",
        action="store_true",
        help="Run from the invoking interpreter; default is a clean venv and dependency solve.",
    )
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise FileNotFoundError(archive)
    archive_hash = sha256(archive)
    with tempfile.TemporaryDirectory(prefix="coastal-reviewer-isolation-") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                destination = (root / member.filename).resolve()
                if not destination.is_relative_to(root.resolve()):
                    raise ValueError(f"Unsafe archive member: {member.filename}")
            package.extractall(root)
        project = root / "major_revision"
        content_manifest = json.loads(
            (project / "major_revision_package_content_manifest.json").read_text(encoding="utf-8")
        )
        expected = {record["path"]: record["sha256"] for record in content_manifest["files"]}
        for record in content_manifest["files"]:
            path = (project / record["path"]).resolve()
            if not path.is_relative_to(project.resolve()):
                raise ValueError("Manifest path escapes extracted project")
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
                raise RuntimeError(f"Archived content mismatch: {record['path']}")
        missing_expected = [path for path in DETERMINISTIC_OUTPUTS if path not in expected]
        if missing_expected:
            raise RuntimeError("Package manifest omits deterministic outputs: " + ", ".join(missing_expected))
        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        if args.reuse_current_environment:
            python = Path(sys.executable)
            environment_scope = "invoking interpreter; archive closure only"
        else:
            environment = root / "venv"
            venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run(
                [str(python), "-m", "pip", "install", "-r", str(project / "requirements-publication.txt")],
                cwd=project,
                check=True,
                env=env,
            )
            subprocess.run([str(python), "-m", "pip", "check"], check=True, env=env)
            environment_scope = "clean temporary venv; dependencies solved from packaged pyproject.toml"
        subprocess.run(
            [str(python), "scripts/reproduce.py", "--mode", "derived"],
            cwd=project,
            check=True,
            env=env,
        )
        mismatches = [
            relative
            for relative in DETERMINISTIC_OUTPUTS
            if sha256(project / relative) != expected[relative]
        ]
        if mismatches:
            raise RuntimeError("Non-deterministic scientific outputs: " + ", ".join(mismatches))
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": archive_hash,
        "status": "PASS",
        "environment_scope": environment_scope,
        "content_hashes_verified": len(expected),
        "deterministic_outputs": DETERMINISTIC_OUTPUTS,
    }
    (ROOT / "reviewer_archive_validation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Reviewer archive derived reproduction: PASS ({len(DETERMINISTIC_OUTPUTS)} deterministic hashes matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

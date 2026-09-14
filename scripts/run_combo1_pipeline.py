#!/usr/bin/env python3

"""Orchestrate Combo 1 download verification and processing."""



from __future__ import annotations



import argparse

import json

import subprocess

import sys

import time

from datetime import datetime, timezone

from pathlib import Path



from combo1_utils import FIGURES, LOGS, PROCESSED, ROOT, ensure_dirs, save_json



SCRIPTS = [

    ("match_stations_to_coastrp", "match_stations_to_coastrp.py"),

    ("merge_gssr_coastrp", "merge_gssr_coastrp.py"),

    ("fetch_open_meteo_climatology", "fetch_open_meteo_climatology.py"),

    ("inundation_sensitivity", "inundation_sensitivity.py --batch-eu"),

    ("generate_combo1_figures", "generate_combo1_figures.py"),

    ("generate_html_reports", "generate_html_reports.py"),

]





def run_step(name: str, script_args: str) -> tuple[bool, float, str]:

    parts = script_args.split()

    script = ROOT / "scripts" / parts[0]

    extra = parts[1:]

    cmd = [sys.executable, str(script), *extra]

    print(f"\n=== {name} ===")

    print(" ".join(cmd))

    t0 = time.perf_counter()

    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)

    elapsed = time.perf_counter() - t0

    if result.stdout:

        print(result.stdout.rstrip())

    if result.stderr:

        print(result.stderr.rstrip(), file=sys.stderr)

    ok = result.returncode == 0

    status = "OK" if ok else f"FAIL (exit {result.returncode})"

    print(f"--- {name}: {status} in {elapsed:.1f}s")

    if not ok:

        tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]

        hint = "\n".join(tail) if tail else "no output captured"

        return False, elapsed, hint

    return True, elapsed, ""





def build_summary() -> dict:

    summary = {

        "generated_at": datetime.now(timezone.utc).isoformat(),

        "pipeline": "combo1",

        "outputs": {},

    }

    for rel in (

        "coast_rp_nearest.parquet",

        "coast_rp_nearest.json",

        "gssr_daily_merged.parquet",

        "rp_comparison.parquet",

        "rp_comparison.json",

        "rp_correlation_meta.json",

        "drivers_daily.parquet",

        "driver_surge_correlations.parquet",

        "inundation_sensitivity.json",

    ):

        p = PROCESSED / rel

        if p.exists():

            summary["outputs"][rel] = p.stat().st_size



    if (PROCESSED / "inundation_sensitivity.json").exists():

        inv = json.loads((PROCESSED / "inundation_sensitivity.json").read_text(encoding="utf-8"))

        summary["inundation_dem_source"] = inv.get("dem_source")



    if (PROCESSED / "rp_comparison.parquet").exists():

        import pandas as pd



        rp = pd.read_parquet(PROCESSED / "rp_comparison.parquet")

        summary["rp_comparison"] = {

            "n_stations": len(rp),

            "mean_rp10_bias_m": float(rp["rp10_bias_m"].mean()),

            "mean_rp100_bias_m": float(rp["rp100_bias_m"].mean()),

        }

        if len(rp) >= 3:

            summary["rp_comparison"]["pearson_rp10"] = float(

                rp[["gssr_rp10_m", "coast_rp_rp10_m"]].corr().iloc[0, 1]

            )

        if "match_flag" in rp.columns:

            summary["rp_comparison"]["n_long_match"] = int((rp["match_flag"] == "long").sum())



    if (PROCESSED / "driver_surge_correlations.parquet").exists():

        import pandas as pd



        dc = pd.read_parquet(PROCESSED / "driver_surge_correlations.parquet")

        summary["met_driver_correlations"] = dc.to_dict(orient="records")



    figs = sorted(
        set(FIGURES.glob("combo1_*.png")) | set(FIGURES.glob("inundation_*.png"))
    )

    summary["figures"] = [str(f.relative_to(ROOT)) for f in figs]

    reports_dir = ROOT / "reports"

    if reports_dir.exists():

        primary = reports_dir / "combo1_complete_report.html"

        summary["html_report_primary"] = str(primary.relative_to(ROOT)) if primary.exists() else None

        summary["html_reports"] = [str(p.relative_to(ROOT)) for p in sorted(reports_dir.glob("*.html"))]

    save_json(PROCESSED / "combo1_summary.json", summary)

    return summary





def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument("--skip-verify", action="store_true")

    args = parser.parse_args()

    ensure_dirs()



    log_lines = [

        f"# Combo1 pipeline run {datetime.now(timezone.utc).isoformat()}\n\n",

        "| Step | Status | Time (s) |\n",

        "| --- | --- | ---: |\n",

    ]

    if not args.skip_verify:

        ok, elapsed, hint = run_step("verify_downloads", "verify_downloads.py --strict")

        log_lines.append(f"| verify_downloads | {'OK' if ok else 'FAIL'} | {elapsed:.1f} |\n")

        if not ok:

            print("Verification failed; continuing with available data.")

            if hint:

                print(f"verify hint:\n{hint}")



    failed = []

    for name, script_args in SCRIPTS:

        ok, elapsed, hint = run_step(name, script_args)

        log_lines.append(f"| {name} | {'OK' if ok else 'FAIL'} | {elapsed:.1f} |\n")

        if not ok:

            failed.append(name)

            if hint:

                log_lines.append(f"\n**{name} error tail:**\n```\n{hint}\n```\n")



    summary = build_summary()

    log_lines.append(f"\n## Summary\n\n- keys: `{list(summary.keys())}`\n")

    if summary.get("html_reports"):

        log_lines.append(f"- HTML reports: `{len(summary['html_reports'])}` files under reports/\n")

    if summary.get("inundation_dem_source"):

        log_lines.append(f"- inundation DEM: `{summary['inundation_dem_source']}`\n")

    if failed:

        log_lines.append(f"- **failed steps**: {', '.join(failed)}\n")



    log_path = LOGS / f"combo1-run-{datetime.now().strftime('%Y%m%d')}.md"

    log_path.write_text("".join(log_lines), encoding="utf-8")

    print(f"\nlog -> {log_path}")

    print(f"summary -> {PROCESSED / 'combo1_summary.json'}")

    print("status dashboard: python scripts\\combo1_status.py")

    if failed:

        print(f"FAILED steps: {', '.join(failed)}")

    return 1 if failed else 0





if __name__ == "__main__":

    raise SystemExit(main())


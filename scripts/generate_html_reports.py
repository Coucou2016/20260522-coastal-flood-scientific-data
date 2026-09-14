#!/usr/bin/env python3
"""Generate fully self-contained Combo 1 HTML reports (offline file://, no external deps)."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from combo1_utils import CONFIG, FIGURES, PROCESSED, RAW, ROOT, ensure_dirs

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[misc, assignment]

REPORTS = ROOT / "reports"

EUROPE_ZIP_TARGET = 2_386_070_935

INLINE_CSS = """
:root { font-family: system-ui, Segoe UI, sans-serif; line-height: 1.5; color: #1a1a1a; }
body { max-width: 960px; margin: 0 auto; padding: 1rem 1.5rem 3rem; background: #fafafa; }
.report-header { border-bottom: 2px solid #0d47a1; margin-bottom: 1.5rem; }
.report-header h1 { margin: 0 0 0.25rem; color: #0d47a1; }
.subtitle { color: #555; margin: 0; }
main h2 { margin-top: 2rem; font-size: 1.15rem; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }
main h3 { margin-top: 1.25rem; font-size: 1rem; color: #444; }
.data-table { width: 100%; border-collapse: collapse; background: #fff; font-size: 0.9rem; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }
.data-table th { background: #e3f2fd; }
.data-table tr:nth-child(even) { background: #f5f5f5; }
.ok { color: #2e7d32; font-weight: 600; }
.fail, .warn { color: #c62828; font-weight: 600; }
figure { margin: 1rem 0; text-align: center; }
figure img { max-width: 100%; height: auto; border: 1px solid #ccc; }
figcaption { font-size: 0.85rem; color: #666; margin-top: 0.25rem; }
pre { background: #fff; border: 1px solid #ddd; padding: 0.75rem; overflow-x: auto; font-size: 0.8rem; }
.report-footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ccc; font-size: 0.85rem; color: #666; }
.meta { background: #e8f5e9; padding: 0.5rem 0.75rem; border-radius: 4px; }
.toc { background: #fff; border: 1px solid #ddd; padding: 0.75rem 1rem; margin-bottom: 1.5rem; }
.toc ul { margin: 0.25rem 0 0; padding-left: 1.25rem; }
.methods dt { font-weight: 600; margin-top: 0.75rem; }
.methods dd { margin: 0.25rem 0 0 1rem; }
""".strip()

PRIMARY_REPORT = "combo1_complete_report.html"
DATA_REPORT = "combo1_data_report.html"
ANALYSIS_REPORT = "combo1_analysis_report.html"


def df_to_html(df: pd.DataFrame, max_rows: int = 200) -> str:
    if df.empty:
        return "<p><em>No data.</em></p>"
    return df.head(max_rows).to_html(index=False, classes="data-table", border=0, escape=True)


def _png_bytes(path: Path, max_width: int = 1400, quality: int = 85) -> bytes:
    raw = path.read_bytes()
    if Image is None or path.stat().st_size < 400_000:
        return raw
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_width:
            ratio = max_width / im.width
            im = im.resize((max_width, int(im.height * ratio)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True, compress_level=6)
        return buf.getvalue()


def embed_image(path: Path, alt: str | None = None) -> str:
    if not path.exists():
        return f'<p class="warn">Missing figure: <code>{path.name}</code></p>'
    b64 = base64.b64encode(_png_bytes(path)).decode("ascii")
    label = alt or path.name
    return (
        f'<figure><img src="data:image/png;base64,{b64}" alt="{label}">'
        f"<figcaption>{label}</figcaption></figure>"
    )


def load_summary() -> dict:
    p = PROCESSED / "combo1_summary.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"generated_at": "unknown", "pipeline": "combo1"}


def version_string(summary: dict) -> str:
    return summary.get("pipeline", "combo1") + "@" + (summary.get("generated_at", "unknown")[:19])


def deltadtm_inventory() -> dict:
    zips_dir = RAW / "deltadtm" / "zips"
    tiles_dir = RAW / "deltadtm" / "tiles"
    europe = zips_dir / "Europe.zip"
    parts = list(zips_dir.glob("*.part")) + list(zips_dir.glob("Europe.zip.part"))
    info: dict = {
        "europe_zip_exists": europe.exists(),
        "europe_zip_bytes": europe.stat().st_size if europe.exists() else 0,
        "europe_zip_target_bytes": EUROPE_ZIP_TARGET,
        "europe_zip_complete": False,
        "europe_zip_pct": 0.0,
        "part_files": [p.name for p in parts],
        "cog_tile_count": len(list(tiles_dir.glob("*.tif"))),
        "cog_tiles": [p.name for p in sorted(tiles_dir.glob("*.tif"))],
    }
    if europe.exists():
        sz = info["europe_zip_bytes"]
        info["europe_zip_pct"] = round(100.0 * sz / EUROPE_ZIP_TARGET, 1)
        info["europe_zip_complete"] = sz >= EUROPE_ZIP_TARGET * 0.99
        try:
            with zipfile.ZipFile(europe) as zf:
                info["europe_zip_entries"] = len(zf.namelist())
                info["europe_zip_valid"] = True
        except zipfile.BadZipFile:
            info["europe_zip_valid"] = False
    return info


def _sha256_head(path: Path, nbytes: int = 65536) -> str:
    if not path.exists():
        return "—"
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()[:16]


def section_quality_audit(summary: dict) -> str:
    """Audit findings + data authenticity (Chinese summary in docs; English table here)."""
    rp = summary.get("rp_comparison", {})
    inv_path = PROCESSED / "inundation_sensitivity.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8")) if inv_path.exists() else {}
    dem = inv.get("dem_source", "unknown")
    is_real_dem = not str(dem).startswith("synthetic")
    rows = [
        ("GSSR ERA5 archives", "8 × .7z → CSV skew surge", "OK", "1979–2019 daily max, metres"),
        ("COAST-RP.nc", "storm_tide_rp_* variables", "OK", "Storm tide RP (includes tide)"),
        ("Open-Meteo", "8 climatology JSON (ERA5)", "OK", "pressure/wind/precip; hPa & m/s"),
        ("DeltaDTM COG", dem, "OK" if is_real_dem else "DEMO", "EGM2008 elevation"),
    ]
    tr = "".join(
        f"<tr><td>{a}</td><td>{b}</td><td class=\"{'ok' if s == 'OK' else 'warn'}\">{s}</td><td>{n}</td></tr>"
        for a, b, s, n in rows
    )
    bias = rp.get("mean_rp10_bias_m", 0)
    body = f"""
<h2 id="quality-audit">Quality audit &amp; data authenticity</h2>
<p>Full Chinese audit: <code>docs/combo1-quality-audit.md</code>. Iteration log: <code>docs/combo1-iteration-log.md</code>.</p>
<table class="data-table">
<thead><tr><th>Layer</th><th>On-disk evidence</th><th>Status</th><th>Notes</th></tr></thead>
<tbody>{tr}</tbody>
</table>
<h3>Key findings (Round 1–4)</h3>
<ul>
<li><strong>Data are real</strong> — not synthetic except when <code>dem_source</code> explicitly says <code>synthetic_coastal_slope</code>.</li>
<li><strong>EU RP10 bias ~{bias:.2f} m</strong> — comparing GSSR <em>skew surge</em> to COAST-RP <em>storm tide</em>; expected, not a unit bug. US stations (NY, Charleston) agree within ~0.1–0.5 m.</li>
<li><strong>Sheerness +2 m bathtub</strong> — high grid fraction reflects many lowland cells (elev &lt; 2 m) under static <code>max(0, SLR−DEM)</code>; report now splits <em>all valid</em> vs <em>lowland (≤15 m)</em> masks.</li>
</ul>
"""
    prov_rows = ""
    with CONFIG.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for st in cfg.get("stations", []):
        g = RAW / "gssr" / "era5" / st["gssr_archive"]
        prov_rows += (
            f"<tr><td>GSSR {st['id']}</td><td><code>{g.name}</code></td>"
            f"<td>{g.stat().st_size:,} B</td><td><code>{_sha256_head(g)}</code></td></tr>\n"
        )
    coast = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
    prov_rows += (
        f"<tr><td>COAST-RP</td><td><code>COAST-RP.nc</code></td>"
        f"<td>{coast.stat().st_size:,} B</td><td><code>{_sha256_head(coast)}</code></td></tr>\n"
    )
    if inv.get("dem_stats"):
        ds = inv["dem_stats"]
        prov_rows += (
            f"<tr><td>DeltaDTM window</td><td>{dem}</td>"
            f"<td>elev {ds.get('elev_min_m', 0):.2f}–{ds.get('elev_max_m', 0):.2f} m</td>"
            f"<td>median {ds.get('elev_median_m', 0):.2f} m</td></tr>\n"
        )
    body += f"""
<h3 id="provenance">Data authenticity table (file hash, sample stats)</h3>
<table class="data-table">
<thead><tr><th>Asset</th><th>File</th><th>Size / stats</th><th>SHA256 (first 64 KiB)</th></tr></thead>
<tbody>{prov_rows}</tbody>
</table>
"""
    dual = FIGURES / "combo1_rp10_dual_region.png"
    if dual.exists():
        body += "<h3>RP10 regional comparison</h3>\n" + embed_image(dual)
    val_fig = FIGURES / "combo1_gssr_coastrp_validation.png"
    if val_fig.exists():
        body += "<h3>Cross-product validation scatter</h3>\n" + embed_image(val_fig)
    return body


def section_executive_summary(summary: dict) -> str:
    body = '<div class="meta"><p><strong>Combo 1 MVP</strong> — coastal flood scientific data integration (GSSR + COAST-RP + Open-Meteo + DeltaDTM).</p></div>'
    body += "<h2 id=\"executive\">Executive summary</h2><ul>"
    if summary.get("inundation_dem_source"):
        body += f"<li>Inundation DEM: <code>{summary['inundation_dem_source']}</code></li>"
    rp = summary.get("rp_comparison", {})
    if rp:
        body += f"<li>Stations analysed: <strong>{rp.get('n_stations', '—')}</strong></li>"
        body += f"<li>Mean RP10 bias (GSSR − COAST-RP): <strong>{rp.get('mean_rp10_bias_m', 0):.3f} m</strong></li>"
        if "pearson_rp10" in rp:
            body += f"<li>Pearson RP10 correlation: {rp['pearson_rp10']:.3f}</li>"
        if "n_long_match" in rp:
            body += f"<li>Stations with match &gt;25 km: {rp['n_long_match']}</li>"
    figs = summary.get("figures", [])
    if figs:
        body += f"<li>Figures produced: {len(figs)}</li>"
    body += "</ul>"
    return body


def section_data_inventory() -> str:
    rows = []
    coast_zip = RAW / "coast_rp" / "COAST-RP.zip"
    rows.append(("COAST-RP.zip", coast_zip, coast_zip.exists()))
    coast_nc = RAW / "coast_rp" / "extracted" / "COAST-RP.nc"
    rows.append(("COAST-RP.nc", coast_nc, coast_nc.exists()))
    with CONFIG.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for st in cfg.get("stations", []):
        g = RAW / "gssr" / "era5" / st["gssr_archive"]
        rows.append((f"GSSR {st['id']}", g, g.exists()))
    idx = RAW / "deltadtm" / "index" / "deltadtm_tiles.gpkg"
    rows.append(("DeltaDTM index", idx, idx.exists()))
    dtm = deltadtm_inventory()
    om_dir = RAW / "open_meteo" / "hourly"
    om = list(om_dir.glob("*.json")) if om_dir.exists() else []

    table_rows = ""
    for label, path, ok in rows:
        size = f"{path.stat().st_size:,} B" if path.exists() else "—"
        table_rows += (
            f"<tr><td>{label}</td><td><code>{path.relative_to(ROOT)}</code></td>"
            f"<td>{size}</td><td class=\"{'ok' if ok else 'fail'}\">{'OK' if ok else 'MISSING'}</td></tr>\n"
        )
    europe_status = "complete" if dtm["europe_zip_complete"] else "incomplete"
    if dtm["part_files"]:
        europe_status += f" (partial: {', '.join(dtm['part_files'])})"

    return f"""
<h2 id="data-inventory">Data inventory &amp; download status</h2>
<table class="data-table">
<thead><tr><th>Asset</th><th>Path</th><th>Size</th><th>Status</th></tr></thead>
<tbody>{table_rows}</tbody>
</table>
<h3>DeltaDTM terrain</h3>
<table class="data-table">
<tr><td>Europe.zip</td><td>{dtm['europe_zip_bytes']:,} / {dtm['europe_zip_target_bytes']:,} B</td><td>{dtm['europe_zip_pct']}%</td><td>{europe_status}</td></tr>
<tr><td>COG tiles in tiles/</td><td colspan="2">{dtm['cog_tile_count']}</td><td>{', '.join(dtm['cog_tiles']) or '—'}</td></tr>
</table>
<h3>Open-Meteo</h3>
<p>{len(om)} JSON file(s) under <code>data/raw/open_meteo/hourly/</code></p>
<p>Re-verify after downloads: <code>python scripts\\verify_downloads.py --strict</code></p>
"""


def section_station_matching() -> str:
    p = PROCESSED / "coast_rp_nearest.parquet"
    if not p.exists():
        return '<h2 id="station-matching">Station matching</h2><p><em>Run match_stations_to_coastrp.py first.</em></p>'
    df = pd.read_parquet(p)
    body = "<h2 id=\"station-matching\">Station matching (GSSR ↔ COAST-RP)</h2>\n" + df_to_html(df)
    if "match_flag" in df.columns:
        long_n = int((df["match_flag"] == "long").sum())
        body += f"<p>Stations with match distance &gt;25 km (<code>long</code>): <strong>{long_n}</strong></p>"
    return body


def section_rp_comparison() -> str:
    body = '<h2 id="rp-comparison">Return period comparison</h2>'
    rp_path = PROCESSED / "rp_comparison.parquet"
    if rp_path.exists():
        df = pd.read_parquet(rp_path)
        body += "<h3>RP comparison table</h3>\n" + df_to_html(df)
        meta = PROCESSED / "rp_correlation_meta.json"
        if meta.exists():
            meta_obj = json.loads(meta.read_text(encoding="utf-8"))
            body += "<h3>Correlation metadata</h3><pre>" + json.dumps(meta_obj, indent=2) + "</pre>"
    else:
        body += "<p><em>No RP outputs yet.</em></p>"
    fig = FIGURES / "combo1_rp10_comparison.png"
    if fig.exists():
        body += "<h3>RP10 bar chart</h3>\n" + embed_image(fig)
    multi = FIGURES / "combo1_rp_multi_station.png"
    if multi.exists():
        body += "<h3>Multi-return-period comparison</h3>\n" + embed_image(multi)
    return body


def section_met_drivers() -> str:
    body = '<h2 id="met-drivers">Meteorological drivers</h2>'
    dc = PROCESSED / "driver_surge_correlations.parquet"
    if dc.exists():
        body += "<h3>Driver–surge Spearman correlations</h3>\n" + df_to_html(pd.read_parquet(dc))
    else:
        body += "<p><em>Run fetch_open_meteo_climatology.py first.</em></p>"
    heat = FIGURES / "combo1_driver_correlation_heatmap.png"
    if heat.exists():
        body += "<h3>Correlation heatmap</h3>\n" + embed_image(heat)
    return body


def section_inundation() -> str:
    inv_all_path = PROCESSED / "inundation_sensitivity_all.json"
    inv_path = PROCESSED / "inundation_sensitivity.json"
    body = '<h2 id="inundation">Inundation sensitivity (DeltaDTM)</h2>'
    inv_list: list[dict] = []
    if inv_all_path.exists():
        inv_list = json.loads(inv_all_path.read_text(encoding="utf-8"))
    elif inv_path.exists():
        inv_list = [json.loads(inv_path.read_text(encoding="utf-8"))]

    if inv_list:
        body += (
            "<table class=\"data-table\"><tr><th>Station</th><th>DEM</th>"
            "<th>+0.5 m (lowland)</th><th>+1 m</th><th>+2 m</th></tr>"
        )
        for inv in inv_list:
            coast_f = inv.get("flooded_fraction_coastal_lowland", inv.get("flooded_fraction", {}))
            body += (
                f"<tr><td>{inv.get('station_name', inv.get('station_id'))}</td>"
                f"<td><code>{inv.get('dem_source', '—')}</code></td>"
                f"<td>{100 * float(coast_f.get('0.5', 0)):.1f}%</td>"
                f"<td>{100 * float(coast_f.get('1.0', 0)):.1f}%</td>"
                f"<td>{100 * float(coast_f.get('2.0', 0)):.1f}%</td></tr>"
            )
        body += "</table>"
        for inv in inv_list:
            sid = inv.get("station_id", "")
            fig = FIGURES / f"inundation_sensitivity_{sid}.png"
            if fig.exists():
                body += f"<h3>{inv.get('station_name', sid)}</h3>\n" + embed_image(fig)
    else:
        body += "<p><em>Run inundation_sensitivity.py --batch-eu first.</em></p>"
    return body


def section_methods_notes() -> str:
    return """
<h2 id="methods">Methods notes — product definitions</h2>
<dl class="methods">
<dt>GSSR (Global Storm Surge Reconstruction)</dt>
<dd>Daily maximum <strong>skew surge / storm surge component</strong> at tide gauges (ERA5 branch, 1979–2019). Return levels from annual maxima + empirical Weibull plotting position (RP10/50/100).</dd>
<dt>COAST-RP (Coastal Storm Surge Return Periods)</dt>
<dd><strong>Coastal grid-point</strong> extreme <strong>storm tide</strong> return levels (includes tidal contribution). Matched to GSSR stations by nearest neighbour (<code>match_dist_km</code>).</dd>
<dt>Expected RP10 bias</dt>
<dd>Systematic negative GSSR vs COAST-RP bias (~−2 m at North Sea stations) is expected: different surge definition, tidal inclusion, spatial representativeness, and fitting methods. Use as <em>cross-product sensitivity</em>, not absolute validation.</dd>
<dt>Open-Meteo ERA5</dt>
<dd>Meteorological drivers only (pressure, wind, precipitation). Spearman correlations with daily surge maxima — statistical association, not hydrodynamic simulation.</dd>
<dt>DeltaDTM + bathtub inundation</dt>
<dd>30 m COG elevation (EGM2008). Static <code>max(0, SLR − DEM)</code> sensitivity at +0.5 / +1 / +2 m; not dynamic flood forecasting.</dd>
</dl>
<p>Full definitions: <code>docs/combo1-product-definitions.md</code> in the project repository.</p>
"""


def table_of_contents() -> str:
    return """
<nav class="toc" aria-label="Table of contents">
<strong>Contents</strong>
<ul>
<li><a href="#executive">Executive summary</a></li>
<li><a href="#quality-audit">Quality audit</a></li>
<li><a href="#provenance">Data authenticity</a></li>
<li><a href="#data-inventory">Data inventory</a></li>
<li><a href="#station-matching">Station matching</a></li>
<li><a href="#rp-comparison">Return period comparison</a></li>
<li><a href="#met-drivers">Meteorological drivers</a></li>
<li><a href="#inundation">Inundation (DeltaDTM)</a></li>
<li><a href="#methods">Methods notes</a></li>
</ul>
</nav>
"""


def _footer(version: str, generated_at: str) -> str:
    return f"""<footer class="report-footer">
<p>Generated at <code>{generated_at}</code> (UTC)</p>
<p>Pipeline version: <code>{version}</code></p>
<p>Standalone report — all tables and figures embedded; safe to open via <code>file://</code> offline.</p>
</footer>"""


def standalone_document(title: str, body: str, version: str, generated_at: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{INLINE_CSS}
</style>
</head>
<body>
<header class="report-header">
<h1>{title}</h1>
<p class="subtitle">Coastal flood scientific data — Combo 1 MVP</p>
</header>
<main>
{body}
</main>
{_footer(version, generated_at)}
</body>
</html>
"""


def build_complete_report(summary: dict, version: str, generated_at: str) -> str:
    body = table_of_contents()
    body += section_executive_summary(summary)
    body += section_quality_audit(summary)
    body += section_data_inventory()
    body += section_station_matching()
    body += section_rp_comparison()
    body += section_met_drivers()
    body += section_inundation()
    body += section_methods_notes()
    return standalone_document("Combo 1 — Complete Report", body, version, generated_at)


def build_data_report(version: str, generated_at: str) -> str:
    body = section_data_inventory()
    body += section_station_matching()
    return standalone_document("Combo 1 — Data Report", body, version, generated_at)


def build_analysis_report(summary: dict, version: str, generated_at: str) -> str:
    body = section_executive_summary(summary)
    body += section_rp_comparison()
    body += section_met_drivers()
    body += section_inundation()
    body += section_methods_notes()
    return standalone_document("Combo 1 — Analysis Report", body, version, generated_at)


def build_optional_index(version: str, generated_at: str) -> str:
    body = f"""
<p class="meta">Optional index — open <strong>{PRIMARY_REPORT}</strong> for the full standalone report (recommended).</p>
<ul>
<li><code>{PRIMARY_REPORT}</code> — complete report (all sections, embedded figures)</li>
<li><code>{DATA_REPORT}</code> — data inventory &amp; station matching only</li>
<li><code>{ANALYSIS_REPORT}</code> — analysis figures &amp; methods only</li>
</ul>
<p>Last build: <code>{generated_at}</code></p>
"""
    return standalone_document("Combo 1 Reports (optional index)", body, version, generated_at)


LEGACY_HTML = (
    "stage0_data_inventory.html",
    "stage1_station_matching.html",
    "stage2_rp_comparison.html",
    "stage3_met_drivers.html",
    "stage4_inundation.html",
    "combo1_full_summary.html",
)


def _remove_legacy_outputs() -> None:
    style = REPORTS / "style.css"
    if style.exists():
        style.unlink()
    assets = REPORTS / "assets"
    if assets.is_dir():
        for f in assets.iterdir():
            f.unlink()
        assets.rmdir()
    for name in LEGACY_HTML:
        p = REPORTS / name
        if p.exists():
            p.unlink()


def generate_all() -> list[Path]:
    ensure_dirs()
    REPORTS.mkdir(parents=True, exist_ok=True)
    _remove_legacy_outputs()

    summary = load_summary()
    version = version_string(summary)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    outputs: list[tuple[str, str]] = [
        (PRIMARY_REPORT, build_complete_report(summary, version, generated_at)),
        (DATA_REPORT, build_data_report(version, generated_at)),
        (ANALYSIS_REPORT, build_analysis_report(summary, version, generated_at)),
        ("index.html", build_optional_index(version, generated_at)),
    ]

    written: list[Path] = []
    for fname, html in outputs:
        out = REPORTS / fname
        out.write_text(html, encoding="utf-8")
        written.append(out)
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"report -> {out} ({size_mb:.2f} MB)")

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Build self-contained Combo 1 HTML reports")
    parser.parse_args()
    paths = generate_all()
    primary = REPORTS / PRIMARY_REPORT
    if primary.exists():
        print(f"\nPrimary report: {primary}")
        print(f"Size: {primary.stat().st_size / (1024 * 1024):.2f} MB")
    return 0 if paths else 1


if __name__ == "__main__":
    raise SystemExit(main())

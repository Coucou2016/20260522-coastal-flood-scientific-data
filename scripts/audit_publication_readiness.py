from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "main"
SOURCE_DIR = ROOT / "data" / "figure_source"
MANUSCRIPT = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript.md"
HTML = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript_review.html"

EXPECTED_FIGURES = [
    "Fig1_process_terrain_design.png",
    "Fig2_water_level_divergence.png",
    "Fig3_meteorological_coherence.png",
    "Fig4_deltadtm_terrain_sensitivity.png",
    "Fig5_process_terrain_typology.png",
]

EXPECTED_PDFS = [name.replace(".png", ".pdf") for name in EXPECTED_FIGURES]
MIN_FIGURE_WIDTH_PX = 3000
MIN_FIGURE_HEIGHT_PX = 1800

EXPECTED_SOURCE_TABLES = [
    "Fig1_station_metadata.csv",
    "Fig2_water_level_divergence.csv",
    "Fig3_driver_correlations.csv",
    "Fig4_connected_terrain_sensitivity.csv",
    "Fig4_hypsometry_curves.csv",
    "Fig5_process_terrain_typology.csv",
    "Table1_data_products.csv",
    "Table2_water_level_indicators.csv",
    "Table3_driver_correlations.csv",
    "Table4_deltadtm_connected_sensitivity.csv",
]


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "img":
            self.images.append(dict(attrs))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def read_csv(name: str) -> pd.DataFrame:
    path = SOURCE_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def check_figure_files(errors: list[str]) -> None:
    for name in EXPECTED_FIGURES:
        path = FIG_DIR / name
        if not path.exists():
            fail(errors, f"Missing PNG figure: {path}")
            continue
        width, height = png_dimensions(path)
        if width < MIN_FIGURE_WIDTH_PX or height < MIN_FIGURE_HEIGHT_PX:
            fail(errors, f"Figure resolution is too low for {name}: {width}x{height}px.")
        if path.stat().st_size < 100_000:
            fail(errors, f"Figure file is suspiciously small: {name} ({path.stat().st_size} bytes).")
    for name in EXPECTED_PDFS:
        path = FIG_DIR / name
        if not path.exists():
            fail(errors, f"Missing PDF figure: {path}")
        elif path.stat().st_size < 10_000:
            fail(errors, f"PDF figure is suspiciously small: {name} ({path.stat().st_size} bytes).")


def check_source_tables(errors: list[str]) -> None:
    for name in EXPECTED_SOURCE_TABLES:
        path = SOURCE_DIR / name
        if not path.exists():
            fail(errors, f"Missing figure/table source CSV: {path}")
            continue
        if path.stat().st_size < 20:
            fail(errors, f"Figure/table source CSV is suspiciously small: {name} ({path.stat().st_size} bytes).")


def check_html(errors: list[str]) -> None:
    if not HTML.exists():
        fail(errors, f"Missing review HTML: {HTML}")
        return
    text = HTML.read_text(encoding="utf-8")
    parser = ImageParser()
    parser.feed(text)
    if len(parser.images) != len(EXPECTED_FIGURES):
        fail(errors, f"HTML embeds {len(parser.images)} images; expected {len(EXPECTED_FIGURES)}.")
    external = sorted(set(re.findall(r"(?:src|href)=[\"'](?!#|data:)([^\"']+)", text)))
    if external:
        fail(errors, "HTML has external dependencies: " + "; ".join(external[:10]))
    for phrase in ["[to be completed]", "to be completed", "待补充", "Repository DOI:", "Repository URL and DOI:"]:
        if phrase in text:
            fail(errors, f"Review HTML still contains submission placeholder: {phrase}")
    if "No data were fabricated" not in text:
        fail(errors, "Review HTML should include the no-fabricated-data statement from the manuscript.")
    html_hashes: dict[str, str] = {}
    for img in parser.images:
        alt = img.get("alt", "")
        src = img.get("src", "")
        if not src.startswith("data:image/png;base64,"):
            fail(errors, f"HTML image {alt!r} is not an embedded PNG data URI.")
            continue
        raw = base64.b64decode(src.split(",", 1)[1])
        html_hashes[alt + ".png"] = hashlib.md5(raw).hexdigest()
    for fig_name in EXPECTED_FIGURES:
        fig_path = FIG_DIR / fig_name
        if not fig_path.exists():
            fail(errors, f"Missing figure file: {fig_path}")
            continue
        file_hash = hashlib.md5(fig_path.read_bytes()).hexdigest()
        if html_hashes.get(fig_name) != file_hash:
            fail(errors, f"HTML embedded image is stale or mismatched for {fig_name}.")


def check_fig2(errors: list[str]) -> None:
    df = read_csv("Fig2_water_level_divergence.csv")
    required = {"station_id", "gssr_rp10_m", "coast_rp_rp10_m", "D10_m", "match_dist_km"}
    missing = required - set(df.columns)
    if missing:
        fail(errors, f"Fig2 source missing columns: {sorted(missing)}")
        return
    calc = df["coast_rp_rp10_m"] - df["gssr_rp10_m"]
    if not (calc - df["D10_m"]).abs().lt(1e-8).all():
        fail(errors, "Fig2 D10_m is not exactly COAST-RP RP10 minus GSSR RP10.")
    if not df["match_dist_km"].le(5).all():
        fail(errors, "Fig2 has at least one COAST-RP match distance > 5 km.")
    if len(df) != 8:
        fail(errors, f"Fig2 should contain eight screening sites, found {len(df)}.")


def check_fig3(errors: list[str]) -> None:
    df = read_csv("Fig3_driver_correlations.csv")
    required = {"station_id", "pressure", "wind", "precipitation", "n_days"}
    missing = required - set(df.columns)
    if missing:
        fail(errors, f"Fig3 source missing columns: {sorted(missing)}")
        return
    rho = df[["pressure", "wind", "precipitation"]]
    if not rho.abs().le(1).all().all():
        fail(errors, "Fig3 contains a correlation coefficient outside [-1, 1].")
    if not df["n_days"].gt(3650).all():
        fail(errors, "Fig3 has too few daily records for at least one station.")
    if len(df) != 8:
        fail(errors, f"Fig3 should contain eight screening sites, found {len(df)}.")


def check_fig4(errors: list[str]) -> None:
    df = read_csv("Fig4_connected_terrain_sensitivity.csv")
    required = {
        "station_id",
        "dem_source",
        "median_lowland_elev_m",
        "connected_0.5m_lowland_pct",
        "bathtub_0.5m_lowland_pct",
        "connected_1m_lowland_pct",
        "bathtub_1m_lowland_pct",
        "connected_2m_lowland_pct",
        "bathtub_2m_lowland_pct",
    }
    missing = required - set(df.columns)
    if missing:
        fail(errors, f"Fig4 source missing columns: {sorted(missing)}")
        return
    if not df["dem_source"].astype(str).str.startswith("DeltaDTM").all():
        fail(errors, "Fig4 includes a non-DeltaDTM DEM source.")
    for level in ("0.5m", "1m", "2m"):
        connected = df[f"connected_{level}_lowland_pct"]
        bathtub = df[f"bathtub_{level}_lowland_pct"]
        if not ((connected >= 0) & (connected <= bathtub) & (bathtub <= 100)).all():
            fail(errors, f"Fig4 connected percentages are invalid for {level}.")
    if df["median_lowland_elev_m"].ge(15).any():
        fail(errors, "Fig4 lowland median elevation should be below the 15 m coastal-lowland mask threshold.")
    if len(df) != 5:
        fail(errors, f"Fig4 should contain five European terrain-screening sites, found {len(df)}.")


def check_fig5(errors: list[str]) -> None:
    fig2 = read_csv("Fig2_water_level_divergence.csv").set_index("station_id")
    fig3 = read_csv("Fig3_driver_correlations.csv").set_index("station_id")
    fig4 = read_csv("Fig4_connected_terrain_sensitivity.csv").set_index("station_id")
    fig5 = read_csv("Fig5_process_terrain_typology.csv").set_index("station_id")
    if len(fig5) != 5:
        fail(errors, f"Fig5 should contain five European terrain-screening sites, found {len(fig5)}.")
    if "median_lowland_elev_m" not in fig5.columns:
        fail(errors, "Fig5 source should report median_lowland_elev_m, not capped full-window median_elev_m.")
    for station_id, row in fig5.iterrows():
        if station_id not in fig2.index or station_id not in fig3.index or station_id not in fig4.index:
            fail(errors, f"Fig5 station is missing from upstream source tables: {station_id}")
            continue
        checks = [
            ("D10_m", row["D10_m"], fig2.loc[station_id, "D10_m"]),
            ("pressure", row["pressure"], fig3.loc[station_id, "pressure"]),
            ("connected_2m_lowland_pct", row["connected_2m_lowland_pct"], fig4.loc[station_id, "connected_2m_lowland_pct"]),
        ]
        if "median_lowland_elev_m" in fig5.columns:
            checks.append(
                ("median_lowland_elev_m", row["median_lowland_elev_m"], fig4.loc[station_id, "median_lowland_elev_m"])
            )
        for name, got, expected in checks:
            if abs(float(got) - float(expected)) > 1e-8:
                fail(errors, f"Fig5 {name} mismatch for {station_id}: {got} != {expected}")


def check_table4(errors: list[str]) -> None:
    path = SOURCE_DIR / "Table4_deltadtm_connected_sensitivity.csv"
    if not path.exists():
        fail(errors, f"Missing Table 4 source: {path}")
        return
    df = pd.read_csv(path)
    if "median_elev_m" in df.columns or "Median elevation (m)" in df.columns:
        fail(errors, "Table 4 still exposes capped full-window median elevation.")
    required = {
        "Station",
        "DEM source",
        "Median coastal-lowland elevation (m)",
        "Ocean-connected +0.5 m (%)",
        "Ocean-connected +1.0 m (%)",
        "Ocean-connected +2.0 m (%)",
        "Non-connected bathtub +2.0 m (%)",
    }
    missing = required - set(df.columns)
    if missing:
        fail(errors, f"Table 4 source missing columns: {sorted(missing)}")
    if "Median coastal-lowland elevation (m)" in df.columns and df["Median coastal-lowland elevation (m)"].ge(15).any():
        fail(errors, "Table 4 lowland median elevation should be below the 15 m coastal-lowland mask threshold.")


def check_algorithm_source(errors: list[str]) -> None:
    source = ROOT / "scripts" / "make_cee_refined_figures.py"
    if not source.exists():
        fail(errors, f"Missing refined figure script: {source}")
        return
    text = source.read_text(encoding="utf-8")
    risky = "np.argwhere(ocean)[0]"
    if risky in text:
        fail(errors, "Connectivity algorithm still seeds an arbitrary interior no-data cell.")
    required = "Interior no-data components were not used as marine seeds"
    manuscript = MANUSCRIPT.read_text(encoding="utf-8") if MANUSCRIPT.exists() else ""
    if required not in manuscript:
        fail(errors, "Manuscript does not state the boundary-only connectivity seed rule.")


def check_manuscript(errors: list[str]) -> None:
    if not MANUSCRIPT.exists():
        fail(errors, f"Missing manuscript: {MANUSCRIPT}")
        return
    text = MANUSCRIPT.read_text(encoding="utf-8")
    forbidden = [
        "synthetic DEM",
        "SYNTHETIC",
        "validates COAST-RP",
        "validates GSSR",
        "Median elevation (m) | Connected lowland",
    ]
    for phrase in forbidden:
        if phrase in text:
            fail(errors, f"Manuscript contains risky phrase: {phrase}")
    required = [
        "ocean-connected",
        "not a flood forecast",
        "physically distinct diagnostics",
        "Median coastal-lowland elevation",
        "10.1038/s41597-021-00906-x",
        "10.4121/13392314",
        "10.1038/s41597-024-03091-9",
        "10.1002/qj.3803",
        "upper-range capped terrain values at 30 m",
    ]
    for phrase in required:
        if phrase not in text:
            fail(errors, f"Manuscript is missing required caution/wording: {phrase}")
    placeholders = [
        "[to be completed]",
        "to be completed",
        "待补充",
        "Repository URL and DOI:",
        "Repository DOI:",
    ]
    for phrase in placeholders:
        if phrase in text:
            fail(errors, f"Manuscript still contains submission placeholder: {phrase}")
    if "No data were fabricated" not in text:
        fail(errors, "Manuscript should explicitly state that no data were fabricated.")


def check_claims_evidence(errors: list[str]) -> None:
    path = ROOT / "manuscript" / "claims_evidence_matrix.md"
    if not path.exists():
        fail(errors, f"Missing claims-evidence matrix: {path}")
        return
    text = path.read_text(encoding="utf-8")
    required = [
        "Figure 2",
        "Figure 3",
        "Figure 4",
        "Figure 5",
        "product-definition divergence",
        "not validation error",
        "Static sensitivity is not observed flood extent",
        "not a trained classifier",
    ]
    for phrase in required:
        if phrase not in text:
            fail(errors, f"Claims-evidence matrix missing required phrase: {phrase}")


def check_submission_support_files(errors: list[str]) -> None:
    required = [
        "target_journal_cee_checklist.md",
        "ai_use_statement_draft.md",
        "data_code_availability_final_draft.md",
        "data_repository_deposit_checklist.md",
        "repository_readme_template.md",
        "citation_metadata_template.md",
        "license_decision_notes.md",
        "supplementary_information_draft.md",
        "review_response_preparation.md",
        "cover_letter_draft.md",
        "editorial_significance_statement.md",
        "publication_release_notes_template.md",
        "submission_metadata_required.md",
        "author_final_confirmation_form.md",
        "title_page_and_declarations_draft.md",
        "submission_package_matrix.md",
        "final_submission_index.md",
        "external_finalization_guide.md",
        "target_journal_cee_checklist.md",
        "nature_reporting_summary_preparation.md",
        "software_environment.md",
    ]
    for name in sorted(set(required)):
        path = ROOT / "manuscript" / name
        if not path.exists():
            fail(errors, f"Missing submission support file: {path}")
        elif path.stat().st_size < 100:
            fail(errors, f"Submission support file is suspiciously small: {name}")
    index_path = ROOT / "manuscript" / "final_submission_index.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        for phrase in ["PUBLICATION READINESS AUDIT: PASS", "publication_package.zip", "completion_status.json", "author_final_confirmation_form.md"]:
            if phrase not in index_text:
                fail(errors, f"Final submission index missing required phrase: {phrase}")


def check_environment_files(errors: list[str]) -> None:
    for rel in ["requirements.txt", "environment.yml", "config/combo1_stations.yaml", "NEXT_ACTIONS.md"]:
        path = ROOT / rel
        if not path.exists():
            fail(errors, f"Missing environment/config file: {path}")
        elif path.stat().st_size < 50:
            fail(errors, f"Environment/config file is suspiciously small: {rel}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit manuscript figures and source tables before publication.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    for check in [
        check_figure_files,
        check_source_tables,
        check_html,
        check_fig2,
        check_fig3,
        check_fig4,
        check_fig5,
        check_table4,
        check_algorithm_source,
        check_manuscript,
        check_claims_evidence,
        check_submission_support_files,
        check_environment_files,
    ]:
        try:
            check(errors)
        except Exception as exc:  # noqa: BLE001 - audit should report all hard failures.
            errors.append(f"{check.__name__} failed: {exc}")
    if errors:
        if not args.quiet:
            print("PUBLICATION READINESS AUDIT: FAIL")
            for err in errors:
                print(f"- {err}")
        return 1
    if not args.quiet:
        print("PUBLICATION READINESS AUDIT: PASS")
        print(f"Checked {len(EXPECTED_FIGURES)} embedded figures, source tables, manuscript cautions and cross-table consistency.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from rasterio.transform import from_origin

from scripts.add_advanced_terrain_rank_diagnostics import cell_center_mesh
from scripts.add_mask_aware_terrain_diagnostics import (
    align_mask_to_dem,
    mask_aware_layers,
    sector_block_bootstrap_assoc,
)
from scripts.add_uncertainty_diagnostics import stable_seed as uncertainty_seed
from scripts.build_nw_europe_extended_diagnostics import stable_seed as extended_seed
from scripts.download_combo1 import extract_zip
from scripts.merge_gssr_coastrp import gssr_empirical_rp
from scripts.make_cee_refined_figures import gssr_empirical_rp_from_annual
from scripts.rebuild_frozen_primary_analysis import classify
from scripts.validate_standalone_html import check_file


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"


def test_raster_cell_centres_follow_north_up_transform() -> None:
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    lon, lat = cell_center_mesh(transform, (2, 2))
    np.testing.assert_allclose(lon, [[0.5, 1.5], [0.5, 1.5]])
    np.testing.assert_allclose(lat, [[1.5, 1.5], [0.5, 0.5]])


def test_mask_alignment_uses_geospatial_transform() -> None:
    source = np.array([[1, 3], [0, 255]], dtype=np.uint8)
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    aligned = align_mask_to_dem(
        source,
        transform,
        "EPSG:4326",
        source.shape,
        transform,
        "EPSG:4326",
    )
    np.testing.assert_array_equal(aligned, source)


def test_official_mask_excludes_lake_and_clipped_classes() -> None:
    mask = np.zeros((5, 5), dtype=np.uint8)
    mask[:, 0] = 1
    mask[:, 1] = 3
    mask[2, 3] = 2
    mask[4, 4] = 255
    elev = np.ones(mask.shape, dtype=float)
    valid = np.ones(mask.shape, dtype=bool)
    layers = mask_aware_layers(elev, valid, mask, 2.0)
    assert layers["tidal_water"][:, :2].all()
    assert not layers["low"][2, 3]
    assert not layers["connected"][2, 3]
    assert not layers["low"][4, 4]
    assert not layers["connected"][4, 4]


def test_river_without_ocean_is_not_a_marine_seed() -> None:
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[:, 0] = 3
    elev = np.ones(mask.shape, dtype=float)
    valid = np.ones(mask.shape, dtype=bool)
    layers = mask_aware_layers(elev, valid, mask, 2.0)
    assert not layers["tidal_water"].any()
    assert not layers["connected"].any()


def test_decomposed_metrics_exclude_clipped_and_outside_support() -> None:
    mask = np.array(
        [
            [1, 1, 1, 1],
            [0, 0, 255, 254],
            [0, 0, 0, 0],
        ],
        dtype=np.uint8,
    )
    elev = np.array(
        [
            [np.nan, np.nan, np.nan, np.nan],
            [1.0, 3.0, np.nan, np.nan],
            [1.0, 1.0, 3.0, 3.0],
        ]
    )
    valid = np.isfinite(elev)
    area = np.ones(mask.shape, dtype=float)
    result = classify(elev, valid, mask, area, mask == 1, 2.0, 4)
    assert result["reference_land_area_km2"] == 6.0
    assert result["below_area_km2"] == 3.0
    assert result["connected_area_km2"] == 3.0
    assert result["below_reference_land_pct"] == 50.0
    assert result["conditional_connectivity_pct"] == 100.0
    assert result["connected_reference_land_pct"] == 50.0


def test_frozen_terrain_grid_obeys_topology_and_metric_contracts() -> None:
    path = SOURCE / "Terrain_robustness_grid_74stations.csv"
    frame = pd.read_csv(path)
    assert len(frame) == 2_960
    assert frame["station_id"].nunique() == 74
    assert frame.groupby("station_id").size().eq(40).all()

    valid = frame.dropna(subset=["below_area_km2", "connected_area_km2"]).copy()
    assert (valid["connected_area_km2"] <= valid["below_area_km2"] + 1e-9).all()
    expected = valid["below_reference_land_pct"] * valid["conditional_connectivity_pct"] / 100.0
    np.testing.assert_allclose(valid["connected_reference_land_pct"], expected, atol=1e-10)

    zero_offset = valid[valid["elevation_offset_m"].eq(0.0)]
    keys = ["station_id", "window_width_km", "eta_m", "seed_rule", "elevation_offset_m"]
    paired = zero_offset.pivot_table(index=keys, columns="neighbours", values="connected_area_km2")
    assert (paired[4] <= paired[8] + 1e-9).all()


def test_primary_workflow_is_four_neighbour_and_complete() -> None:
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    assert len(primary) == 68
    assert primary["station_id"].nunique() == 68
    assert primary["neighbours"].eq(4).all()
    assert primary["window_width_km"].eq(10.0).all()
    assert primary["eta_m"].eq(2.0).all()
    assert primary["match_dist_km"].le(6.0).all()
    assert (primary["connected_area_km2"] <= primary["below_area_km2"] + 1e-9).all()
    assert (primary["below_area_km2"] <= primary["reference_land_area_km2"] + 1e-9).all()
    assert (primary["reference_land_area_km2"] <= primary["window_area_km2"] + 1e-9).all()


def test_return_period_and_spatial_null_outputs_are_complete() -> None:
    rp = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    assert set(rp["return_period_years"]) == {2, 5, 10, 25, 50, 100}
    assert set(rp["terrain_metric_label"]) >= {
        "lowland_prevalence",
        "conditional_connectivity",
        "connected_lowland_share",
        "connected_area",
    }
    assert rp.groupby("return_period_years")["terrain_metric"].nunique().eq(5).all()
    assert rp["n_permutations"].eq(10_000).all()

    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    assert set(topk["top_share_pct"]) == set(range(10, 41))
    top20 = topk[topk["top_share_pct"].eq(20)].iloc[0]
    assert int(top20["top_n"]) == 14
    assert int(top20["observed_overlap"]) == 1
    assert float(top20["sector_stratified_null_q025"]) <= 1 <= float(top20["sector_stratified_null_q975"])


def test_match_distance_and_tidal_provenance_contracts() -> None:
    audit = pd.read_csv(SOURCE / "Match_distance_audit_74stations.csv")
    included = audit[audit["included_in_primary_match_sample"].astype(bool)]
    excluded = audit[~audit["included_in_primary_match_sample"].astype(bool)]
    assert len(included) == 68
    assert len(excluded) == 6
    assert included["recomputed_match_dist_km"].le(6.0).all()
    assert excluded["recomputed_match_dist_km"].gt(6.0).all()

    tidal = pd.read_csv(SOURCE / "FigS1_tidal_source_audit.csv")
    assert len(tidal) == 13
    assert tidal["source_status"].eq("source_verified").all()
    assert tidal["plotted_count"].eq(13).all()
    assert tidal["coordinate_duplicate_count"].eq(1).all()


def test_topology_and_local_dtm_outputs_match_primary_definition() -> None:
    topology = pd.read_csv(SOURCE / "Topology_sensitivity_summary.csv")
    connected = topology[topology["terrain_metric"].eq("connected_reference_land_pct")].iloc[0]
    assert float(connected["rank_spearman_4n_vs_8n"]) > 0.9
    assert int(connected["membership_changes"]) > 0

    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")
    assert len(local) == 7
    assert local["land_connectivity_neighbour_rule"].eq(4).all()


def test_submission_text_and_figure_contracts() -> None:
    manuscript = (ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript.md").read_text(encoding="utf-8")
    assert "Hino et al. (2025). Operationalising Nature Futures" not in manuscript
    assert "Article 383" not in manuscript
    assert "**6**, 404 (2025)" in manuscript
    assert "primary:10km,2m,8n" not in manuscript
    assert "Fig4_metric_decomposition_robustness" in (ROOT / "scripts" / "build_standalone_paper.py").read_text(encoding="utf-8")
    assert (ROOT / "figures" / "main" / "Fig4_metric_decomposition_robustness.pdf").is_file()


def test_empirical_return_levels_do_not_extrapolate() -> None:
    years = pd.date_range("2000-01-01", periods=25, freq="YS")
    frame = pd.DataFrame({"date": years, "surge_m": np.arange(1.0, 26.0)})
    levels = gssr_empirical_rp(frame, [10, 50, 100])
    assert np.isfinite(levels[10])
    assert np.isnan(levels[50])
    assert np.isnan(levels[100])
    assert np.isclose(levels[10], 23.4)


def test_figure_bootstrap_uses_the_same_empirical_estimator() -> None:
    annual = np.arange(1.0, 26.0)
    assert np.isclose(gssr_empirical_rp_from_annual(annual, 10), 23.4)
    assert np.isnan(gssr_empirical_rp_from_annual(annual, 50))


def test_random_seeds_are_stable_and_shared() -> None:
    assert uncertainty_seed("sheerness") == uncertainty_seed("sheerness")
    assert uncertainty_seed("sheerness") == extended_seed("sheerness")
    assert uncertainty_seed("sheerness") != uncertainty_seed("newlyn")


def test_sector_block_bootstrap_reports_ordered_intervals() -> None:
    frame = pd.DataFrame(
        {
            "station_id": [f"s{i}" for i in range(12)],
            "lon": [-6.0, -5.5, -4.0, -3.0, -0.5, 0.5, 1.0, 2.0, 4.0, 6.0, 9.0, 10.0],
            "lat": [50.0, 51.0, 49.0, 50.0, 53.0, 54.0, 50.0, 51.0, 52.0, 53.0, 55.0, 56.0],
            "coast_rp_rp10_m": np.arange(12.0, 0.0, -1.0),
            "terrain": np.arange(1.0, 13.0),
        }
    )
    result = sector_block_bootstrap_assoc(frame, "synthetic", "terrain", n_boot=100, seed=7)
    assert result["n_coastal_sectors"] >= 4
    assert result["spearman_block_p025"] <= result["spearman_block_p500"]
    assert result["spearman_block_p500"] <= result["spearman_block_p975"]


def test_standalone_html_validator_checks_active_and_css_resources(tmp_path) -> None:
    html = tmp_path / "bad.html"
    html.write_text(
        '<!DOCTYPE html><html><head><style>.x{background:url("remote.png")}</style></head>'
        '<body><img srcset="data:image/png;base64,AA 1x, https://example.org/x.png 2x">'
        '<a href="javascript:alert(1)">x</a></body></html>',
        encoding="utf-8",
    )
    issues = check_file(html)
    assert any("<style>" in issue for issue in issues)
    assert any("srcset" in issue for issue in issues)
    assert any("javascript" in issue for issue in issues)


def test_zip_extraction_rejects_path_traversal(tmp_path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "blocked")
    with pytest.raises(ValueError, match="unsafe ZIP member"):
        extract_zip(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()

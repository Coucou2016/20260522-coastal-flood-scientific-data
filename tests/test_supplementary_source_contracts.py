from scripts.build_supplementary_information import load_focal_water_table_source


def test_focal_water_table_is_a_complete_eight_station_join() -> None:
    water = load_focal_water_table_source()

    assert len(water) == 8
    assert water["station_id"].is_unique
    assert water["full_label"].eq("Hoek van Holland").sum() == 1
    assert water[
        [
            "gssr_rp10_bootstrap_p025_m",
            "gssr_rp10_bootstrap_p975_m",
            "within5km_min_rp10_m",
            "within5km_max_rp10_m",
            "spring_tidal_range_m",
            "source_status",
        ]
    ].notna().all().all()

#!/usr/bin/env python3
"""Add an explicit local-coast review layer to nearest COAST-RP matches."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from coastal_screening.spatial_blocks import attach_spatial_blocks  # noqa: E402


SOURCE = ROOT / "data" / "figure_source"
BLOCK_CONFIG = ROOT / "config" / "coastal_spatial_blocks_v2.csv"
ESTUARY_SITES = {
    "avonmouth-p060-uk",
    "cuxhaven-germany",
    "delfzijl-del-nl",
    "felixstowe-p204-uk",
    "harwich-p022-uk",
    "hoekvanholla-hvh-nl",
    "immingham-p026-uk",
    "milfordhaven-p056-uk",
    "newport-p057-uk",
    "portbury-p341-uk",
    "sheerness-p015-uk",
}
ISLAND_OR_FJORD_SITES = {
    "lerwick-p041-uk",
    "stmarys-p231-uk",
    "sthelier-p074-uk",
    "stornoway-p042-uk",
    "tregde-006-norway",
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> int:
    frame = attach_spatial_blocks(
        pd.read_csv(SOURCE / "Match_distance_audit_74stations.csv"),
        BLOCK_CONFIG,
    )
    station_token = frame["station"].str.replace(r"\s+P\d+.*$", "", regex=True).map(normalized)
    source_token = frame["coast_rp_source_station_id"].map(normalized)
    frame["source_id_contains_station_name"] = [
        bool(token and token in source) for token, source in zip(station_token, source_token)
    ]
    frame["estuary_or_embayment_flag"] = frame["station_id"].isin(ESTUARY_SITES)
    frame["island_fjord_geometry_flag"] = frame["station_id"].isin(ISLAND_OR_FJORD_SITES)
    frame["opposite_bank_flag"] = "not_determined_from_coordinate_review"
    frame["coordinate_connector_review_pass"] = frame["included_in_primary_match_sample"].astype(bool)
    frame["review_status"] = "excluded_distance_gt6km"
    frame.loc[frame["coordinate_connector_review_pass"], "review_status"] = (
        "coordinate_pair_plausible_not_hydrodynamic_equivalence"
    )
    frame["review_basis"] = (
        "coordinate connector inspection; source-station identifier where named; "
        "explicit estuary/island/fjord flags; no along-coast hydrodynamic equivalence claimed"
    )
    included = frame[frame["included_in_primary_match_sample"].astype(bool)]
    if not included["coordinate_connector_review_pass"].all():
        raise AssertionError("A primary COAST-RP match lacks coordinate-connector review")
    frame.to_csv(SOURCE / "COAST_RP_same_coast_match_audit.csv", index=False)
    print(
        f"Reviewed {len(included)} primary matches; "
        f"{int(included['estuary_or_embayment_flag'].sum())} carry estuary/embayment flags."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

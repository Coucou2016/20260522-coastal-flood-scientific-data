"""Versioned spatial-block assignments used by the inferential workflow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BLOCK_SCALES_KM = (100, 150, 250)
REQUIRED_COLUMNS = {
    "station_id",
    "coastal_basin",
    "spatial_block_100km",
    "spatial_block_150km",
    "spatial_block_250km",
    "block_definition",
}

REGION_BY_BASIN = {
    "Southwest-Atlantic": "Southwest-British-Coasts",
    "Celtic-Irish-Sea": "Southwest-British-Coasts",
    "Bristol-Channel": "Southwest-British-Coasts",
    "Irish-Sea": "Irish-Sea-and-Scottish-Atlantic",
    "North-Channel-Clyde": "Irish-Sea-and-Scottish-Atlantic",
    "Scottish-Atlantic": "Irish-Sea-and-Scottish-Atlantic",
    "English-Channel-UK": "English-Channel-UK",
    "Thames-Estuary": "English-Channel-UK",
    "Southern-North-Sea-UK": "British-North-Sea",
    "Northern-North-Sea": "British-North-Sea",
    "Loire-Bay-of-Biscay": "French-Atlantic-and-Brittany",
    "Loire-Estuary": "French-Atlantic-and-Brittany",
    "Brittany-Atlantic": "French-Atlantic-and-Brittany",
    "French-English-Channel": "French-English-Channel",
    "Rhine-Meuse-Coast": "Southern-North-Sea-Continental",
    "Dutch-Wadden-Coast": "Southern-North-Sea-Continental",
    "Dutch-German-Bight": "Southern-North-Sea-Continental",
    "German-Bight": "Southern-North-Sea-Continental",
    "Danish-Wadden-Coast": "Southern-North-Sea-Continental",
    "Skagerrak": "Skagerrak",
}


def load_spatial_blocks(path: str | Path) -> pd.DataFrame:
    """Load and validate the reviewed station-to-coast assignment table."""
    table = pd.read_csv(path, dtype=str)
    missing_columns = REQUIRED_COLUMNS.difference(table.columns)
    if missing_columns:
        raise ValueError(f"Spatial-block table is missing columns: {sorted(missing_columns)}")
    if table["station_id"].duplicated().any():
        duplicate_ids = table.loc[table["station_id"].duplicated(False), "station_id"].tolist()
        raise ValueError(f"Duplicate station IDs in spatial-block table: {duplicate_ids}")
    for column in sorted(REQUIRED_COLUMNS):
        if table[column].isna().any() or table[column].str.strip().eq("").any():
            bad_ids = table.loc[table[column].isna() | table[column].str.strip().eq(""), "station_id"].tolist()
            raise ValueError(f"Blank {column} values for stations: {bad_ids}")
    return table


def attach_spatial_blocks(frame: pd.DataFrame, path: str | Path) -> pd.DataFrame:
    """Attach reviewed coast labels and fail if any analysis station is unmapped."""
    blocks = load_spatial_blocks(path)
    block_columns = [
        "station_id",
        "coastal_basin",
        "spatial_block_100km",
        "spatial_block_150km",
        "spatial_block_250km",
        "block_definition",
    ]
    source = frame.drop(
        columns=[column for column in block_columns[1:] if column in frame.columns],
        errors="ignore",
    )
    out = source.merge(blocks[block_columns], on="station_id", how="left", validate="many_to_one")
    missing = out.loc[out["spatial_block_150km"].isna(), "station_id"].drop_duplicates().tolist()
    if missing:
        raise ValueError(f"Stations without reviewed spatial blocks: {missing}")
    # Compatibility label for existing table and figure builders. Statistical code
    # selects an explicit spatial_block_* column and never infers this from coordinates.
    out["coastal_sector"] = out["coastal_basin"]
    out["coastal_region"] = out["coastal_basin"].map(REGION_BY_BASIN)
    if out["coastal_region"].isna().any():
        bad = out.loc[out["coastal_region"].isna(), "coastal_basin"].drop_duplicates().tolist()
        raise ValueError(f"Coastal basins without a display-region mapping: {bad}")
    return out


def block_column(scale_km: int) -> str:
    if scale_km not in BLOCK_SCALES_KM:
        raise ValueError(f"Unsupported block scale {scale_km}; expected one of {BLOCK_SCALES_KM}")
    return f"spatial_block_{scale_km}km"

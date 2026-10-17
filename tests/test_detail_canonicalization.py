from io import StringIO

import pandas as pd

from scripts.rebuild_frozen_primary_analysis import canonicalize_detail


def test_detail_canonicalization_is_csv_roundtrip_idempotent() -> None:
    frame = pd.DataFrame(
        {
            "station_id": ["a"],
            "eta_m": [2.0],
            "connected_reference_land_pct": [99.99999999999997],
            "coastal_basin": ["basin"],
            "spatial_block_150km": ["B01"],
            "station": ["A"],
        }
    )

    first = canonicalize_detail(frame)
    buffer = StringIO()
    first.to_csv(buffer, index=False)
    second = canonicalize_detail(pd.read_csv(StringIO(buffer.getvalue())))

    pd.testing.assert_frame_equal(first, second)
    assert first.loc[0, "connected_reference_land_pct"] == 100.0
    assert list(first.columns[:3]) == ["station_id", "station", "coastal_basin"]

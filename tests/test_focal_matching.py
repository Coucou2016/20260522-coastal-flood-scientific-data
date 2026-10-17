"""Regression for degree-space versus great-circle nearest neighbours."""

import numpy as np
from scripts import match_stations_to_coastrp as matching


def test_matching_uses_great_circle_distance():
    # At 60N, one degree east is closer than 0.75 degrees north,
    # despite the opposite ordering in unscaled longitude/latitude space.
    index, distance = matching.nearest_great_circle_index(
        0.0,
        60.0,
        np.array([1.0, 0.0]),
        np.array([60.0, 60.75]),
    )
    assert index == 0
    assert np.isclose(distance, 55.597, atol=0.01)

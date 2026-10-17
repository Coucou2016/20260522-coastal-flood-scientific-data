"""Compatibility and numerical contracts for threshold integration."""

import numpy as np
import pytest

from scripts.add_threshold_integrated_terrain_metric import threshold_average


def test_threshold_average_matches_linear_analytic_mean():
    levels = np.array([0.0, 1.0, 2.0, 3.0])
    values = 2.0 * levels + 1.0
    assert threshold_average(values, levels) == pytest.approx(4.0)


def test_threshold_average_rejects_zero_span():
    with pytest.raises(ValueError, match="positive interval"):
        threshold_average(np.array([2.0]), np.array([1.0]))

"""Auditable statistical primitives shared across analysis scripts."""

from __future__ import annotations

import numpy as np


def empirical_two_sided_p(null: np.ndarray, observed: float) -> float:
    """Two-sided permutation p-value from empirical lower and upper tails."""
    values = np.asarray(null, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0 or not np.isfinite(observed):
        return float("nan")
    p_lower = (1.0 + np.sum(values <= observed)) / (values.size + 1.0)
    p_upper = (1.0 + np.sum(values >= observed)) / (values.size + 1.0)
    return float(min(1.0, 2.0 * min(p_lower, p_upper)))


def deterministic_top_k(values: np.ndarray, station_ids: np.ndarray, k: int) -> np.ndarray:
    """Select exactly k largest values with station ID as a documented tie-break."""
    values = np.asarray(values, dtype=float)
    station_ids = np.asarray(station_ids, dtype=str)
    if values.ndim != 1 or station_ids.ndim != 1 or values.size != station_ids.size:
        raise ValueError("values and station_ids must be one-dimensional arrays of equal length")
    if not 0 < k <= values.size:
        raise ValueError(f"k must be between 1 and {values.size}, got {k}")
    if not np.isfinite(values).all():
        raise ValueError("top-k values must all be finite")
    return np.lexsort((station_ids, -values))[:k]


def deterministic_top_k_rows(values: np.ndarray, station_ids: np.ndarray, k: int) -> np.ndarray:
    """Vectorized deterministic top-k selection for a matrix of null draws."""
    matrix = np.asarray(values, dtype=float)
    station_ids = np.asarray(station_ids, dtype=str)
    if matrix.ndim != 2 or matrix.shape[1] != station_ids.size:
        raise ValueError("values must be rows x stations and match station_ids")
    if not 0 < k <= station_ids.size:
        raise ValueError(f"k must be between 1 and {station_ids.size}, got {k}")
    id_order = np.argsort(station_ids, kind="stable")
    ordered = matrix[:, id_order]
    # Pre-order columns by station ID, then use a stable descending value sort.
    # Tied values therefore retain ascending station-ID order in every row.
    positions = np.argsort(-ordered, axis=1, kind="stable")[:, :k]
    return id_order[positions]


def symmetric_distance_weights(
    lat: np.ndarray,
    lon: np.ndarray,
    distances_km: np.ndarray,
    threshold_km: float,
) -> np.ndarray:
    """Build symmetric binary weights, linking isolates to their nearest neighbour."""
    del lat, lon  # Coordinates are accepted for an explicit API but distances drive weights.
    distances = np.asarray(distances_km, dtype=float)
    if distances.ndim != 2 or distances.shape[0] != distances.shape[1]:
        raise ValueError("distances_km must be a square matrix")
    weights = ((distances > 0.0) & (distances <= threshold_km)).astype(float)
    for index in np.flatnonzero(weights.sum(axis=1) == 0.0):
        row = distances[index].copy()
        row[index] = np.inf
        nearest = int(np.argmin(row))
        weights[index, nearest] = 1.0
        weights[nearest, index] = 1.0
    return np.maximum(weights, weights.T)

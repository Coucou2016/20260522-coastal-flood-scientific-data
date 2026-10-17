"""Explicit raster-connectivity operations used by terrain screening."""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


STRUCTURES = {
    4: ndi.generate_binary_structure(2, 1),
    8: ndi.generate_binary_structure(2, 2),
}


def connectivity_structure(neighbours: int) -> np.ndarray:
    try:
        return STRUCTURES[int(neighbours)]
    except KeyError as exc:
        raise ValueError("neighbours must be 4 or 8") from exc


def connected_component(seed: np.ndarray, passable: np.ndarray, neighbours: int) -> np.ndarray:
    """Propagate seed cells through an explicitly selected raster topology."""
    seed = np.asarray(seed, dtype=bool)
    passable = np.asarray(passable, dtype=bool)
    if seed.shape != passable.shape:
        raise ValueError("seed and passable arrays must have identical shapes")
    return ndi.binary_propagation(
        seed & passable,
        structure=connectivity_structure(neighbours),
        mask=passable,
    )


def ocean_connected_water(ocean: np.ndarray, river: np.ndarray, neighbours: int) -> np.ndarray:
    """Return ocean cells plus river cells connected to ocean under one topology."""
    ocean = np.asarray(ocean, dtype=bool)
    river = np.asarray(river, dtype=bool)
    return connected_component(ocean, ocean | river, neighbours)

"""Core scientific methods for the coastal-screening analysis."""

from .spatial_blocks import attach_spatial_blocks, load_spatial_blocks
from .statistics import deterministic_top_k, empirical_two_sided_p

__all__ = [
    "attach_spatial_blocks",
    "deterministic_top_k",
    "empirical_two_sided_p",
    "load_spatial_blocks",
]

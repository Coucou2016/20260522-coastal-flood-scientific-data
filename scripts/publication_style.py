#!/usr/bin/env python3
"""Shared SciencePlots settings for manuscript and report figures."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401  # registers the SciencePlots styles


def apply_publication_style() -> None:
    """Apply the project-wide journal figure style."""
    plt.style.use(["science", "no-latex"])
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 9.0,
            "axes.titlesize": 9.5,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "figure.titlesize": 11.0,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.5,
            "lines.markersize": 5.0,
            "grid.linewidth": 0.45,
            "grid.alpha": 0.38,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.dpi": 160,
            "savefig.dpi": 450,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "savefig.transparent": False,
        }
    )


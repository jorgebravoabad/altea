"""Reproducible figure generation.

Deterministic, publication-oriented figures: orthogonal slice montages, QC
score panels with dropped slices highlighted, pore-size distributions and
acquisition convergence curves. Every figure is a pure function of its inputs
so the panels in a paper can be regenerated exactly from the saved outputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless, deterministic
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..core import Volume  # noqa: E402


def orthoslices(volume: Volume, path: Optional[str] = None):
    """Show the three central orthogonal slices of a volume."""
    d = volume.data
    zc, yc, xc = (s // 2 for s in d.shape)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, img, title in zip(
        axes,
        (d[zc], d[:, yc, :], d[:, :, xc]),
        ("z (axial)", "y", "x"),
    ):
        ax.imshow(img, cmap="gray")
        ax.set_title(title)
        ax.axis("off")
    fig.tight_layout()
    return _finish(fig, path)


def qc_panel(report, path: Optional[str] = None):
    """Plot per-slice QC metrics with dropped slices highlighted."""
    idx = [s.index for s in report.slices]
    sharp = [s.sharpness for s in report.slices]
    drift = [s.drift for s in report.slices]
    dropped = set(report.dropped_indices)

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for ax, series, name in zip(axes, (sharp, drift), ("sharpness", "drift (px)")):
        ax.plot(idx, series, "-", color="0.4", lw=1)
        ax.scatter(
            [i for i in idx if i not in dropped],
            [v for i, v in zip(idx, series) if i not in dropped],
            s=10, color="tab:blue", label="kept",
        )
        if dropped:
            ax.scatter(
                [i for i in idx if i in dropped],
                [v for i, v in zip(idx, series) if i in dropped],
                s=30, color="tab:red", marker="x", label="dropped",
            )
        ax.set_ylabel(name)
        ax.legend(loc="best", fontsize=8)
    axes[-1].set_xlabel("slice index")
    fig.suptitle("Automated slice quality control")
    fig.tight_layout()
    return _finish(fig, path)


def psd_plot(report, path: Optional[str] = None):
    """Plot a pore-size distribution from a MorphometryReport."""
    centers = np.asarray(report.psd.get("bin_centers", []))
    pdf = np.asarray(report.psd.get("pdf", []))
    fig, ax = plt.subplots(figsize=(7, 4))
    if centers.size:
        ax.bar(centers, pdf, width=(centers[1] - centers[0]) if centers.size > 1 else 1,
               color="tab:blue", alpha=0.8)
    ax.set_xlabel(f"pore diameter ({report.units})")
    ax.set_ylabel("volume fraction")
    ax.set_title("Pore-size distribution")
    fig.tight_layout()
    return _finish(fig, path)


def convergence_plot(result, tol: Optional[float] = None, path: Optional[str] = None):
    """Plot descriptor relative error versus slice budget."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(result.n_slices, result.relative_errors(), "o-", color="tab:purple")
    if tol is not None:
        ax.axhline(tol, ls="--", color="0.5", label=f"tolerance = {tol:g}")
        n = result.slices_for_tolerance(tol)
        if n is not None:
            ax.axvline(n, ls=":", color="tab:green",
                       label=f"sufficient budget = {n} slices")
        ax.legend(fontsize=8)
    ax.set_xlabel("number of slices")
    ax.set_ylabel(f"relative error in {result.descriptor}")
    ax.set_title("Acquisition convergence")
    fig.tight_layout()
    return _finish(fig, path)


def _finish(fig, path: Optional[str]):
    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150)
        plt.close(fig)
        return p
    return fig

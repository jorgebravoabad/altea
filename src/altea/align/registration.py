"""Inter-slice drift correction (rigid stack registration).

FIB-SEM stacks accumulate translational drift between sections. This module
estimates the slice-to-slice rigid shift by phase cross-correlation, integrates
it into an absolute displacement per slice, and resamples the stack onto a
common frame. All estimated shifts are returned so they can be recorded in the
provenance log.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy import ndimage as ndi
from skimage.registration import phase_cross_correlation

from ..core import Volume


def estimate_drift(volume: Volume, upsample_factor: int = 10) -> np.ndarray:
    """Estimate cumulative (y, x) drift for each slice, in pixels.

    The first slice defines the reference frame (zero shift). Each subsequent
    shift is measured relative to the previous slice and accumulated.
    """
    data = volume.data.astype(np.float32)
    nz = data.shape[0]
    shifts = np.zeros((nz, 2), dtype=np.float64)
    for z in range(1, nz):
        shift, _, _ = phase_cross_correlation(
            data[z - 1], data[z],
            upsample_factor=upsample_factor,
            normalization=None,
        )
        shifts[z] = shifts[z - 1] + np.asarray(shift)
    return shifts


def apply_drift(volume: Volume, shifts: np.ndarray, order: int = 1) -> Volume:
    """Resample each slice by the negative of its estimated drift."""
    data = volume.data.astype(np.float32)
    out = np.empty_like(data)
    for z in range(data.shape[0]):
        out[z] = ndi.shift(
            data[z], shift=shifts[z], order=order, mode="nearest"
        )
    return volume.with_data(out.astype(volume.dtype))


def correct_drift(
    volume: Volume, upsample_factor: int = 10
) -> Tuple[Volume, np.ndarray]:
    """Estimate and correct drift in one call.

    Returns the aligned volume and the per-slice shift array (for provenance).
    """
    shifts = estimate_drift(volume, upsample_factor=upsample_factor)
    aligned = apply_drift(volume, shifts)
    return aligned, shifts

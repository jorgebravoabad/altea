"""Synthetic tomographic data with known ground truth.

These generators let the whole pipeline be exercised, tested and demonstrated
*without any proprietary data*. A Gaussian-random-field threshold model produces
a porous structure whose porosity is prescribed exactly, so segmentation and
morphometry can be validated against a known answer. Acquisition artefacts
(drift, blur, streaks, intensity drift) can be layered on top to exercise the
quality-control module.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy import ndimage as ndi

from ..core import Volume


def gaussian_random_field(
    shape: Tuple[int, int, int],
    correlation_length: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return a zero-mean, unit-variance Gaussian random field."""
    noise = rng.standard_normal(shape)
    field = ndi.gaussian_filter(noise, sigma=correlation_length)
    field -= field.mean()
    std = field.std()
    if std > 0:
        field /= std
    return field


def make_porous_volume(
    shape: Tuple[int, int, int] = (64, 128, 128),
    porosity: float = 0.35,
    correlation_length: float = 4.0,
    spacing: Tuple[float, float, float] = (10.0, 5.0, 5.0),
    solid_intensity: float = 180.0,
    pore_intensity: float = 60.0,
    seed: Optional[int] = 0,
) -> Tuple[Volume, np.ndarray]:
    """Generate a synthetic two-phase porous volume.

    Returns
    -------
    volume:
        A grayscale :class:`~altea.core.Volume` resembling a raw acquisition.
    ground_truth:
        Boolean array, ``True`` inside the pore phase. Prescribed porosity is
        matched by construction (up to voxelization).
    """
    rng = np.random.default_rng(seed)
    field = gaussian_random_field(shape, correlation_length, rng)
    # Threshold at the porosity-th percentile so pore fraction == porosity.
    threshold = np.quantile(field, porosity)
    pore = field < threshold  # True in pore phase

    gray = np.where(pore, pore_intensity, solid_intensity).astype(np.float32)
    volume = Volume(
        data=gray,
        spacing=spacing,
        units="nm",
        metadata={"source": "synthetic", "target_porosity": porosity},
    )
    return volume, pore


def add_acquisition_artifacts(
    volume: Volume,
    *,
    noise_sigma: float = 8.0,
    drift_px: float = 1.5,
    blur_slices: Optional[Tuple[int, ...]] = None,
    charge_slices: Optional[Tuple[int, ...]] = None,
    curtain_strength: float = 0.0,
    seed: Optional[int] = 1,
) -> Volume:
    """Corrupt a clean volume with realistic FIB-SEM artefacts.

    The corruptions mirror the defects a human operator removes by hand:
    inter-slice drift, isolated blurred sections, charging (intensity spikes)
    and vertical curtaining streaks. Used to demonstrate that the QC module
    recovers the bad slices reproducibly.
    """
    rng = np.random.default_rng(seed)
    data = volume.data.astype(np.float32).copy()
    nz = data.shape[0]

    # Cumulative random-walk drift in y and x.
    if drift_px > 0:
        shifts = np.cumsum(rng.normal(0, drift_px, size=(nz, 2)), axis=0)
        for z in range(nz):
            data[z] = ndi.shift(
                data[z], shift=shifts[z], order=1, mode="nearest"
            )

    # Localized blur (defocus / re-deposition).
    for z in blur_slices or ():
        if 0 <= z < nz:
            data[z] = ndi.gaussian_filter(data[z], sigma=3.0)

    # Charging: large additive brightness offset on isolated slices.
    for z in charge_slices or ():
        if 0 <= z < nz:
            data[z] = data[z] + 90.0

    # Curtaining: vertical streaks (constant along y, random along x).
    if curtain_strength > 0:
        streak = rng.normal(0, curtain_strength, size=(1, 1, data.shape[2]))
        data = data + streak

    # Sensor noise.
    if noise_sigma > 0:
        data = data + rng.normal(0, noise_sigma, size=data.shape)

    data = np.clip(data, 0, 255)
    return volume.with_data(data.astype(np.float32))

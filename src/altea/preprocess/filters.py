"""Deterministic preprocessing: denoising and contrast normalization.

The acquisition team described their current image treatment as being "like
Photoshop": filters and contrast/brightness adjustments tuned by eye, sample by
sample, with no single reproducible procedure. This module offers the same
operations but fully parameterized -- every choice is an explicit argument that
is captured in the run's provenance record, so the treatment applied to a
sample can be reproduced exactly and compared across samples.
"""
from __future__ import annotations

import numpy as np
from skimage import exposure
from skimage.restoration import denoise_bilateral, denoise_nl_means
from scipy import ndimage as ndi

from ..core import Volume


def denoise(
    volume: Volume,
    method: str = "median",
    *,
    size: int = 3,
    sigma: float = 1.0,
    bilateral_sigma_color: float = 0.1,
    bilateral_sigma_spatial: float = 1.0,
) -> Volume:
    """Apply a deterministic denoising filter slice-wise.

    Parameters
    ----------
    method:
        One of ``"median"``, ``"gaussian"``, ``"bilateral"``, ``"nlmeans"``.
    """
    data = volume.data.astype(np.float32)
    out = np.empty_like(data)

    if method == "median":
        for z in range(data.shape[0]):
            out[z] = ndi.median_filter(data[z], size=size)
    elif method == "gaussian":
        for z in range(data.shape[0]):
            out[z] = ndi.gaussian_filter(data[z], sigma=sigma)
    elif method in ("bilateral", "nlmeans"):
        for z in range(data.shape[0]):
            sl = data[z]
            lo, hi = sl.min(), sl.max()
            norm = (sl - lo) / (hi - lo + 1e-8)
            if method == "bilateral":
                den = denoise_bilateral(
                    norm,
                    sigma_color=bilateral_sigma_color,
                    sigma_spatial=bilateral_sigma_spatial,
                )
            else:
                den = denoise_nl_means(norm, h=bilateral_sigma_color)
            out[z] = den * (hi - lo) + lo
    else:
        raise ValueError(f"Unknown denoise method: {method!r}")

    return volume.with_data(out.astype(volume.dtype))


def normalize_contrast(
    volume: Volume,
    method: str = "percentile",
    *,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    clip_limit: float = 0.01,
) -> Volume:
    """Deterministic contrast normalization to the [0, 1] range.

    Parameters
    ----------
    method:
        ``"percentile"`` rescales between the given percentiles (computed over
        the whole volume, so all slices share one mapping). ``"clahe"`` applies
        contrast-limited adaptive histogram equalization slice-wise.
    """
    data = volume.data.astype(np.float32)
    if method == "percentile":
        lo = np.percentile(data, low_percentile)
        hi = np.percentile(data, high_percentile)
        out = exposure.rescale_intensity(
            data, in_range=(lo, hi), out_range=(0.0, 1.0)
        )
    elif method == "clahe":
        out = np.empty_like(data)
        rng = data.max() - data.min() + 1e-8
        norm = (data - data.min()) / rng
        for z in range(data.shape[0]):
            out[z] = exposure.equalize_adapthist(
                norm[z], clip_limit=clip_limit
            )
    else:
        raise ValueError(f"Unknown normalize method: {method!r}")
    return volume.with_data(out.astype(np.float32))

"""Classical, unsupervised segmentation backends.

These provide fast, dependency-light baselines and a reference point against
which learned backends are compared. For a two-phase porous medium, global
Otsu thresholding is often a strong baseline; watershed is offered for
splitting touching objects when instance labels are required.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu, threshold_local
from skimage.segmentation import watershed
from skimage.feature import peak_local_max

from ...core import Volume
from ..base import SegmentationBackend, register_backend


@register_backend
class OtsuThreshold(SegmentationBackend):
    """Binary segmentation by Otsu's method.

    Parameters
    ----------
    invert:
        If ``True``, label voxels *below* the threshold as foreground (use for
        pore phases that are darker than the solid).
    mode:
        ``"global"`` for a single stack-wide threshold, or ``"local"`` for a
        slice-wise adaptive threshold.
    block_size:
        Neighborhood size for ``mode="local"`` (odd integer).
    """

    name = "otsu"

    def predict(self, volume: Volume) -> np.ndarray:
        invert = self.params.get("invert", True)
        mode = self.params.get("mode", "global")
        data = volume.data.astype(np.float32)

        if mode == "global":
            t = threshold_otsu(data)
            mask = data < t if invert else data > t
        elif mode == "local":
            block = int(self.params.get("block_size", 35))
            mask = np.empty(data.shape, dtype=bool)
            for z in range(data.shape[0]):
                t = threshold_local(data[z], block_size=block)
                mask[z] = data[z] < t if invert else data[z] > t
        else:
            raise ValueError(f"Unknown mode {mode!r}")
        return mask


@register_backend
class WatershedSplit(SegmentationBackend):
    """Instance segmentation of the foreground phase by distance watershed.

    A foreground mask is obtained by Otsu, then split into labeled objects
    using the watershed transform on the distance map. Useful when connected
    pores or grains must be separated for per-object statistics.
    """

    name = "watershed"

    def predict(self, volume: Volume) -> np.ndarray:
        invert = self.params.get("invert", True)
        min_distance = int(self.params.get("min_distance", 5))
        data = volume.data.astype(np.float32)

        t = threshold_otsu(data)
        mask = data < t if invert else data > t

        distance = ndi.distance_transform_edt(mask)
        coords = peak_local_max(
            distance, min_distance=min_distance, labels=mask
        )
        markers = np.zeros(distance.shape, dtype=np.int32)
        for i, c in enumerate(coords, start=1):
            markers[tuple(c)] = i
        labels = watershed(-distance, markers, mask=mask)
        return labels.astype(np.int32)

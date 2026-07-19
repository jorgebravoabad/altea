"""Learned segmentation: a random-forest pixel classifier.

This is the trainable, "machine-learning" baseline and the direct open-source
analog of the pixel classifiers built into commercial tools (Ilastik, and the
ML segmentation in Avizo/Amira). A bank of local image features (intensity,
smoothed intensity, gradients, texture) is computed per voxel; a random forest
learns to map those features to phase labels from a handful of annotated
slices. Because it needs only sparse annotations, it is well suited to FIB-SEM
data where dense 3-D labeling is prohibitively expensive.

Deep backends (e.g. a 2-D U-Net / nnU-Net) implement the same
:class:`~altea.segment.base.SegmentationBackend` interface and can be added
under the optional ``deep`` extra without changing any pipeline code.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import RandomForestClassifier

from ..base import SegmentationBackend, register_backend


def _feature_stack(slice_2d: np.ndarray, sigmas: List[float]) -> np.ndarray:
    """Compute a per-pixel feature stack for one slice.

    Returns an array of shape ``(H, W, n_features)``.
    """
    s = slice_2d.astype(np.float32)
    feats = [s]
    for sigma in sigmas:
        sm = ndi.gaussian_filter(s, sigma)
        feats.append(sm)
        # gradient magnitude at this scale
        gy, gx = np.gradient(sm)
        feats.append(np.hypot(gx, gy))
        # local variance (texture) at this scale
        mean = ndi.uniform_filter(s, size=int(2 * sigma + 1))
        sqmean = ndi.uniform_filter(s * s, size=int(2 * sigma + 1))
        feats.append(np.maximum(sqmean - mean * mean, 0.0))
    return np.stack(feats, axis=-1)


@register_backend
class PixelClassifier(SegmentationBackend):
    """Random-forest pixel classifier over a multi-scale feature stack.

    Parameters
    ----------
    sigmas:
        Gaussian scales at which features are computed.
    n_estimators, max_depth, random_state:
        Passed to :class:`sklearn.ensemble.RandomForestClassifier`. ``random_state``
        is fixed by default so training is reproducible.
    """

    name = "pixel_rf"

    def __init__(self, **params) -> None:
        super().__init__(**params)
        self.sigmas: List[float] = list(params.get("sigmas", [1.0, 2.0, 4.0]))
        self.clf = RandomForestClassifier(
            n_estimators=int(params.get("n_estimators", 100)),
            max_depth=params.get("max_depth", None),
            random_state=int(params.get("random_state", 0)),
            n_jobs=int(params.get("n_jobs", -1)),
        )
        self._fitted = False

    def fit(self, volume, labels: Optional[np.ndarray] = None) -> "PixelClassifier":
        """Train from (sparse) labels.

        ``labels`` must be an integer array broadcastable to the volume shape,
        with a designated ``ignore_label`` (default ``-1`` or ``0``) marking
        unannotated voxels. Voxels with a valid label contribute training rows.
        """
        if labels is None:
            raise ValueError("PixelClassifier.fit requires labels.")
        ignore = self.params.get("ignore_label", -1)
        data = volume.data
        X_parts, y_parts = [], []
        for z in range(data.shape[0]):
            lab = labels[z]
            if np.all(lab == ignore):
                continue
            feats = _feature_stack(data[z], self.sigmas)
            m = lab != ignore
            if not np.any(m):
                continue
            X_parts.append(feats[m])
            y_parts.append(lab[m])
        if not X_parts:
            raise ValueError("No annotated voxels found for training.")
        X = np.concatenate(X_parts, axis=0)
        y = np.concatenate(y_parts, axis=0)
        self.clf.fit(X, y)
        self._fitted = True
        return self

    def predict(self, volume) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("PixelClassifier must be fit before predict.")
        data = volume.data
        out = np.empty(data.shape, dtype=np.int32)
        for z in range(data.shape[0]):
            feats = _feature_stack(data[z], self.sigmas)
            H, W, F = feats.shape
            pred = self.clf.predict(feats.reshape(-1, F))
            out[z] = pred.reshape(H, W)
        return out

"""Optional deep-learning segmentation backend (extension point).

This module documents how a deep backend plugs into ALTEA. It is intentionally
lazy about importing ``torch`` so the core package installs and runs without
heavy dependencies. Install the deep extra to enable it::

    pip install "altea[deep]"

A production deep backend (for example a 2-D U-Net trained slice-wise, or an
nnU-Net wrapper) only needs to subclass
:class:`~altea.segment.base.SegmentationBackend` and register itself. Because it
shares the interface with the classical and random-forest backends, no pipeline
or configuration schema changes are required to adopt it -- selecting it is a
one-line change in the YAML config.
"""
from __future__ import annotations

import numpy as np

from ..base import SegmentationBackend, register_backend


@register_backend
class TorchUNet(SegmentationBackend):
    """Slice-wise 2-D U-Net backend (requires the ``deep`` extra).

    The 2-D slice-wise default is deliberate: FIB-SEM stacks are typically
    anisotropic (fine in-plane, coarser along z), and 2-D models need far fewer
    annotations than 3-D ones. A 3-D variant can be added the same way for
    near-isotropic voxels.

    This reference implementation raises a clear error until a trained model is
    supplied, so the extension point is discoverable without shipping weights.
    """

    name = "unet"

    def __init__(self, **params) -> None:
        super().__init__(**params)
        self._model = params.get("model", None)
        try:  # pragma: no cover - optional dependency
            import torch  # noqa: F401
            self._torch_available = True
        except Exception:
            self._torch_available = False

    def fit(self, volume, labels=None):  # pragma: no cover - needs torch
        if not self._torch_available:
            raise ImportError(
                "TorchUNet requires the optional 'deep' extra: "
                "pip install 'altea[deep]'."
            )
        raise NotImplementedError(
            "Provide a training loop or pass a pre-trained `model=` to TorchUNet. "
            "See docs/segmentation.md for a reference U-Net skeleton."
        )

    def predict(self, volume) -> np.ndarray:  # pragma: no cover - needs torch
        if self._model is None:
            raise NotImplementedError(
                "No model supplied. Pass model=<trained_module> or use the "
                "'pixel_rf' backend for a dependency-light learned baseline."
            )
        import torch

        self._model.eval()
        data = volume.data.astype(np.float32)
        out = np.empty(data.shape, dtype=np.int32)
        with torch.no_grad():
            for z in range(data.shape[0]):
                x = torch.from_numpy(data[z])[None, None]
                logits = self._model(x)
                out[z] = logits.argmax(1)[0].cpu().numpy()
        return out

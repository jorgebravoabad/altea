"""Segmentation backend interface and registry.

Segmentation is the stage most likely to be swapped as methods evolve, so it is
kept behind a small, stable interface. Backends register themselves by name;
selecting or replacing one (Otsu today, a random-forest pixel classifier next,
a deep network tomorrow) is a configuration change rather than a code change.
This is what lets the framework's identity stay "the reproducible orchestration
layer" rather than "the thing that runs one particular model".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Type

import numpy as np

from ..core import Volume


class SegmentationBackend(ABC):
    """Abstract base class for all segmentation backends.

    A backend maps a grayscale :class:`~altea.core.Volume` to a binary or
    labeled array of the same shape. Supervised backends may implement
    :meth:`fit`; unsupervised ones can leave it as a no-op.
    """

    name: str = "base"

    def __init__(self, **params) -> None:
        self.params = params

    def fit(self, volume: Volume, labels: Optional[np.ndarray] = None) -> "SegmentationBackend":
        """Optionally train on labeled data. Default: no training required."""
        return self

    @abstractmethod
    def predict(self, volume: Volume) -> np.ndarray:
        """Return a segmentation array with the same shape as ``volume.data``."""
        raise NotImplementedError

    def fit_predict(self, volume: Volume, labels: Optional[np.ndarray] = None) -> np.ndarray:
        return self.fit(volume, labels).predict(volume)


_REGISTRY: Dict[str, Type[SegmentationBackend]] = {}


def register_backend(cls: Type[SegmentationBackend]) -> Type[SegmentationBackend]:
    """Class decorator that registers a backend under its ``name``."""
    key = getattr(cls, "name", None)
    if not key or key == "base":
        raise ValueError("Backend must define a unique class attribute `name`.")
    _REGISTRY[key] = cls
    return cls


def get_backend(name: str, **params) -> SegmentationBackend:
    """Instantiate a registered backend by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown segmentation backend {name!r}. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](**params)


def available_backends() -> list[str]:
    return sorted(_REGISTRY)

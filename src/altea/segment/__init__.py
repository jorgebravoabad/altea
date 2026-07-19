"""Segmentation: pluggable backends behind a common interface."""
from .base import (
    SegmentationBackend,
    available_backends,
    get_backend,
    register_backend,
)
# Import backend modules so they self-register.
from . import classical as _classical  # noqa: F401
from . import learned as _learned  # noqa: F401

__all__ = [
    "SegmentationBackend",
    "register_backend",
    "get_backend",
    "available_backends",
]

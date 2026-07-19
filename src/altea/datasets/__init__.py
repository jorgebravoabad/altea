"""Synthetic and reference datasets for testing and demonstration."""
from .synthetic import (
    add_acquisition_artifacts,
    gaussian_random_field,
    make_porous_volume,
)

__all__ = [
    "make_porous_volume",
    "add_acquisition_artifacts",
    "gaussian_random_field",
]

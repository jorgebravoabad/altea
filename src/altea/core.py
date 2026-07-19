"""Core data structures shared across ALTEA modules.

The central object is :class:`Volume`, a thin wrapper around a 3-D NumPy array
that additionally carries the physical voxel spacing and free-form metadata.
Carrying the spacing with the data is what allows every downstream descriptor
(surface area, pore size, tortuosity) to be reported in physical units and to
remain correct for the anisotropic voxels typical of FIB-SEM acquisitions.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

# Voxel spacing is stored in (z, y, x) order, matching NumPy array axes.
Spacing = Tuple[float, float, float]


@dataclass
class Volume:
    """A 3-D image volume with physical voxel spacing.

    Parameters
    ----------
    data:
        3-D array with axes ordered ``(z, y, x)``. ``z`` is the slice /
        sectioning axis (the FIB milling direction for FIB-SEM).
    spacing:
        Physical size of a voxel along ``(z, y, x)`` in ``units``.
    units:
        Length unit of ``spacing`` (default ``"nm"``).
    metadata:
        Free-form acquisition metadata (instrument, pixel dwell, etc.).
    """

    data: np.ndarray
    spacing: Spacing = (1.0, 1.0, 1.0)
    units: str = "nm"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data)
        if self.data.ndim != 3:
            raise ValueError(
                f"Volume expects a 3-D array (z, y, x); got ndim={self.data.ndim}."
            )
        if len(self.spacing) != 3:
            raise ValueError("spacing must have three entries (z, y, x).")
        self.spacing = tuple(float(s) for s in self.spacing)

    # -- convenience -----------------------------------------------------
    @property
    def shape(self) -> Tuple[int, int, int]:
        return self.data.shape  # type: ignore[return-value]

    @property
    def n_slices(self) -> int:
        return int(self.data.shape[0])

    @property
    def dtype(self) -> np.dtype:
        return self.data.dtype

    @property
    def voxel_volume(self) -> float:
        """Physical volume of a single voxel."""
        dz, dy, dx = self.spacing
        return dz * dy * dx

    @property
    def anisotropy(self) -> float:
        """Ratio of the z spacing to the in-plane spacing.

        Values well above 1 flag anisotropic stacks, for which slice-wise 2-D
        processing is usually preferable to isotropic 3-D processing.
        """
        dz, dy, dx = self.spacing
        return dz / float(np.mean([dy, dx]))

    def with_data(self, data: np.ndarray) -> "Volume":
        """Return a copy carrying ``data`` but the same spacing/metadata."""
        return Volume(
            data=data,
            spacing=self.spacing,
            units=self.units,
            metadata=dict(self.metadata),
        )

    def hash(self) -> str:
        """Content hash of the array bytes (for provenance records)."""
        h = hashlib.sha256()
        h.update(str(self.data.shape).encode())
        h.update(str(self.data.dtype).encode())
        h.update(np.ascontiguousarray(self.data).tobytes())
        return h.hexdigest()

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"Volume(shape={self.shape}, dtype={self.dtype}, "
            f"spacing={self.spacing} {self.units})"
        )

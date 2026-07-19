"""Reading and writing tomographic stacks.

Supports multi-page TIFF files and directories of single-page TIFFs (the two
formats FIB-SEM exports most commonly). Voxel spacing is read from TIFF
resolution tags when present and can always be overridden explicitly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np
import tifffile

from ..core import Spacing, Volume

_TIFF_SUFFIXES = {".tif", ".tiff"}


def _read_multipage(path: Path) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.ndim == 2:  # single slice
        arr = arr[np.newaxis, ...]
    if arr.ndim != 3:
        raise ValueError(f"Expected a 2-D or 3-D TIFF, got shape {arr.shape}.")
    return arr


def _read_directory(path: Path) -> np.ndarray:
    files = sorted(
        p for p in path.iterdir() if p.suffix.lower() in _TIFF_SUFFIXES
    )
    if not files:
        raise FileNotFoundError(f"No TIFF slices found in {path}.")
    planes = [tifffile.imread(str(p)) for p in files]
    shapes = {p.shape for p in planes}
    if len(shapes) != 1:
        raise ValueError(f"Inconsistent slice shapes in {path}: {shapes}.")
    return np.stack(planes, axis=0)


def load_stack(
    path: str | Path,
    spacing: Optional[Spacing] = None,
    units: str = "nm",
) -> Volume:
    """Load a stack from a multi-page TIFF or a directory of TIFFs.

    Parameters
    ----------
    path:
        Path to a ``.tif``/``.tiff`` file or a directory of slice files.
    spacing:
        Voxel spacing ``(z, y, x)``. If ``None``, an attempt is made to read
        the in-plane spacing from TIFF resolution tags; unknown axes default
        to ``1.0``.
    units:
        Length unit associated with ``spacing``.
    """
    path = Path(path)
    if path.is_dir():
        data = _read_directory(path)
        read_spacing = None
    elif path.suffix.lower() in _TIFF_SUFFIXES:
        data = _read_multipage(path)
        read_spacing = _spacing_from_tiff(path)
    else:
        raise ValueError(f"Unsupported input: {path}")

    final_spacing: Spacing = spacing or read_spacing or (1.0, 1.0, 1.0)
    return Volume(
        data=data,
        spacing=final_spacing,
        units=units,
        metadata={"source_path": str(path)},
    )


def _spacing_from_tiff(path: Path) -> Optional[Spacing]:
    """Best-effort in-plane spacing from TIFF resolution tags."""
    try:
        with tifffile.TiffFile(str(path)) as tf:
            page = tf.pages[0]
            tags = page.tags
            if "XResolution" in tags and "YResolution" in tags:
                xr = tags["XResolution"].value
                yr = tags["YResolution"].value
                # resolution is stored as pixels-per-unit (a rational)
                dx = xr[1] / xr[0] if xr[0] else 1.0
                dy = yr[1] / yr[0] if yr[0] else 1.0
                return (1.0, float(dy), float(dx))
    except Exception:  # pragma: no cover - tags are optional
        return None
    return None


def save_stack(volume: Volume, path: str | Path) -> Path:
    """Write a volume to a multi-page TIFF, preserving spacing in metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dz, dy, dx = volume.spacing
    tifffile.imwrite(
        str(path),
        volume.data,
        metadata={"spacing_zyx": list(volume.spacing), "units": volume.units},
        resolution=(1.0 / dx if dx else 1.0, 1.0 / dy if dy else 1.0),
    )
    return path


def save_labels(labels: np.ndarray, path: str | Path) -> Path:
    """Write a label/mask volume to a multi-page TIFF."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = labels.astype(np.uint16) if labels.dtype != bool else labels.astype(np.uint8)
    tifffile.imwrite(str(path), arr)
    return path

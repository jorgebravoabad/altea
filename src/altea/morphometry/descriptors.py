"""Quantitative 3-D morphometry of a segmented phase.

Given a binary volume (``True`` in the phase of interest, typically the pore
space) and the physical voxel spacing, these functions compute the descriptors
that go into the scientific figures: porosity, specific surface area, pore-size
distribution, connectivity/percolation and geometric tortuosity. All quantities
respect anisotropic voxel spacing and are returned in physical units.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

from ..core import Volume


# --------------------------------------------------------------------------
# Scalar descriptors
# --------------------------------------------------------------------------
def porosity(mask: np.ndarray) -> float:
    """Volume fraction of the ``True`` phase."""
    return float(mask.mean())


def specific_surface_area(mask: np.ndarray, spacing: Tuple[float, float, float]) -> float:
    """Interfacial area per unit total volume (units: 1 / length).

    The interface is meshed with marching cubes (respecting anisotropic
    spacing) and its area divided by the total physical volume.
    """
    if not mask.any() or mask.all():
        return 0.0
    verts, faces, _, _ = measure.marching_cubes(
        mask.astype(np.float32), level=0.5, spacing=spacing
    )
    area = measure.mesh_surface_area(verts, faces)
    dz, dy, dx = spacing
    total_volume = mask.size * dz * dy * dx
    return float(area / total_volume)


def connectivity(mask: np.ndarray) -> Dict[str, object]:
    """Connected-component summary of the phase.

    Returns the number of components, the fraction of phase voxels belonging to
    the largest one, and whether the phase percolates (connects opposite faces)
    along each axis.
    """
    labeled, n = ndi.label(mask)
    result: Dict[str, object] = {"n_components": int(n)}
    if n == 0:
        result.update(
            largest_fraction=0.0, percolates_z=False,
            percolates_y=False, percolates_x=False, percolates_any=False,
        )
        return result

    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0  # background
    largest = int(sizes.argmax())
    result["largest_fraction"] = float(sizes[largest] / mask.sum())

    perc = {}
    for axis, key in zip(range(3), ("percolates_z", "percolates_y", "percolates_x")):
        first = set(np.unique(np.take(labeled, 0, axis=axis)))
        last = set(np.unique(np.take(labeled, -1, axis=axis)))
        shared = (first & last) - {0}
        perc[key] = bool(shared)
    result.update(perc)
    result["percolates_any"] = bool(any(perc.values()))
    return result


# --------------------------------------------------------------------------
# Pore-size distribution (granulometry)
# --------------------------------------------------------------------------
def pore_size_distribution(
    mask: np.ndarray,
    spacing: Tuple[float, float, float],
    n_bins: int = 20,
) -> Dict[str, np.ndarray]:
    """Continuous pore-size distribution by distance-transform granulometry.

    A pore voxel is assigned the diameter of the largest sphere that both fits
    inside the pore phase and contains it (the local-thickness definition,
    approximated via the Euclidean distance transform). The distribution is the
    volume-weighted histogram of those diameters.

    Returns a dict with ``bin_centers`` (physical length), ``pdf`` (volume
    fraction per bin) and the ``mean``/``median`` pore diameter.
    """
    if not mask.any():
        return {
            "bin_centers": np.array([]),
            "pdf": np.array([]),
            "mean": 0.0,
            "median": 0.0,
        }
    # Distance from each pore voxel to the nearest solid, in physical units.
    dist = ndi.distance_transform_edt(mask, sampling=spacing)
    # Local thickness: propagate the maximal enclosing-sphere radius.
    radius = _local_thickness(mask, dist)
    diameters = 2.0 * radius[mask]

    hi = diameters.max()
    edges = np.linspace(0, hi, n_bins + 1)
    counts, _ = np.histogram(diameters, bins=edges)
    pdf = counts / counts.sum() if counts.sum() else counts.astype(float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return {
        "bin_centers": centers,
        "pdf": pdf,
        "mean": float(diameters.mean()),
        "median": float(np.median(diameters)),
    }


def _local_thickness(mask: np.ndarray, dist: np.ndarray) -> np.ndarray:
    """Approximate local thickness from a distance map.

    For each candidate radius (descending), voxels within that radius of a
    distance-map maximum of at least that radius are assigned the radius. This
    is a standard, dependency-light approximation of the local-thickness /
    granulometry measure.
    """
    thickness = np.zeros_like(dist)
    radii = np.unique(np.round(dist[mask], 2))
    radii = radii[radii > 0][::-1]
    for r in radii:
        seeds = dist >= r
        if not seeds.any():
            continue
        # Dilate seeds by r (in voxels, using an isotropic approximation on the
        # distance map) and fill where not yet assigned.
        reach = ndi.distance_transform_edt(~seeds) <= r
        assign = reach & mask & (thickness == 0)
        thickness[assign] = r
    thickness[mask & (thickness == 0)] = dist[mask & (thickness == 0)]
    return thickness


# --------------------------------------------------------------------------
# Geometric tortuosity
# --------------------------------------------------------------------------
def geometric_tortuosity(
    mask: np.ndarray,
    spacing: Tuple[float, float, float],
    axis: int = 0,
) -> float:
    """Geometric tortuosity of the percolating phase along ``axis``.

    Computed as the mean geodesic path length through the phase from the entry
    face to the exit face, divided by the straight-line domain length. Returns
    ``nan`` if the phase does not percolate along the chosen axis.

    A multi-source breadth-first / Dijkstra front is propagated through pore
    voxels from the entry face; the mean arrival distance at the exit face gives
    the geodesic length. Intended for the moderate volume sizes typical of a
    representative subvolume.
    """
    labeled, n = ndi.label(mask)
    if n == 0:
        return float("nan")

    entry = np.take(labeled, 0, axis=axis)
    exit_ = np.take(labeled, -1, axis=axis)
    shared = (set(np.unique(entry)) & set(np.unique(exit_))) - {0}
    if not shared:
        return float("nan")

    perc = np.isin(labeled, list(shared))
    geo = _geodesic_from_face(perc, spacing, axis)

    exit_slice = np.take(geo, geo.shape[axis] - 1, axis=axis)
    exit_mask = np.take(perc, perc.shape[axis] - 1, axis=axis)
    valid = exit_mask & np.isfinite(exit_slice)
    if not valid.any():
        return float("nan")

    mean_geodesic = float(exit_slice[valid].mean())
    straight = (mask.shape[axis] - 1) * spacing[axis]
    return mean_geodesic / straight if straight > 0 else float("nan")


def _geodesic_from_face(
    perc: np.ndarray, spacing: Tuple[float, float, float], axis: int
) -> np.ndarray:
    """Dijkstra geodesic distance from the entry face through ``perc`` voxels."""
    import heapq

    geo = np.full(perc.shape, np.inf, dtype=np.float64)
    # 6-connected neighborhood with physical step lengths.
    steps = []
    for a in range(3):
        for s in (-1, 1):
            off = [0, 0, 0]
            off[a] = s
            steps.append((tuple(off), spacing[a]))

    heap: List[Tuple[float, Tuple[int, int, int]]] = []
    face_index = [slice(None)] * 3
    face_index[axis] = 0
    entry_coords = np.argwhere(perc[tuple(face_index)])
    for coord in entry_coords:
        full = list(coord[:axis]) + [0] + list(coord[axis:])
        # rebuild full 3-D index with the entry plane inserted at `axis`
        idx = [0, 0, 0]
        c = list(coord)
        j = 0
        for a in range(3):
            if a == axis:
                idx[a] = 0
            else:
                idx[a] = c[j]
                j += 1
        idx = tuple(idx)
        geo[idx] = 0.0
        heapq.heappush(heap, (0.0, idx))

    shape = perc.shape
    while heap:
        d, idx = heapq.heappop(heap)
        if d > geo[idx]:
            continue
        for off, cost in steps:
            nb = (idx[0] + off[0], idx[1] + off[1], idx[2] + off[2])
            if (
                0 <= nb[0] < shape[0]
                and 0 <= nb[1] < shape[1]
                and 0 <= nb[2] < shape[2]
                and perc[nb]
            ):
                nd = d + cost
                if nd < geo[nb]:
                    geo[nb] = nd
                    heapq.heappush(heap, (nd, nb))
    return geo


# --------------------------------------------------------------------------
# Aggregate report
# --------------------------------------------------------------------------
@dataclass
class MorphometryReport:
    """All morphometric descriptors for one segmented volume."""

    porosity: float
    specific_surface_area: float
    connectivity: Dict[str, object]
    psd: Dict[str, object]
    tortuosity: Dict[str, float] = field(default_factory=dict)
    units: str = "nm"

    def to_dict(self) -> Dict[str, object]:
        return {
            "porosity": self.porosity,
            "specific_surface_area": self.specific_surface_area,
            "specific_surface_area_units": f"1/{self.units}",
            "connectivity": self.connectivity,
            "psd": {
                "mean_diameter": self.psd.get("mean"),
                "median_diameter": self.psd.get("median"),
                "bin_centers": np.asarray(self.psd.get("bin_centers", [])).tolist(),
                "pdf": np.asarray(self.psd.get("pdf", [])).tolist(),
            },
            "tortuosity": self.tortuosity,
            "length_units": self.units,
        }


def analyze(
    mask: np.ndarray,
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    *,
    units: str = "nm",
    compute_tortuosity: bool = True,
    psd_bins: int = 20,
) -> MorphometryReport:
    """Compute the full morphometric report for a binary mask."""
    mask = np.asarray(mask, dtype=bool)
    tort: Dict[str, float] = {}
    if compute_tortuosity:
        for axis, key in zip(range(3), ("z", "y", "x")):
            tort[key] = geometric_tortuosity(mask, spacing, axis=axis)
    return MorphometryReport(
        porosity=porosity(mask),
        specific_surface_area=specific_surface_area(mask, spacing),
        connectivity=connectivity(mask),
        psd=pore_size_distribution(mask, spacing, n_bins=psd_bins),
        tortuosity=tort,
        units=units,
    )


def analyze_volume(volume: Volume, mask: np.ndarray, **kwargs) -> MorphometryReport:
    """Analyze ``mask`` using the spacing/units carried by ``volume``."""
    return analyze(mask, spacing=volume.spacing, units=volume.units, **kwargs)

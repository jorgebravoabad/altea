"""Acquisition analysis: how few slices are enough?

FIB-SEM acquisition is the dominant cost (5-10 hours of destructive beam time
per sample on an expensive instrument), and that cost scales with the number of
slices collected. This module quantifies the trade-off between the number of
slices and the accuracy of the resulting morphometric descriptors: it
sub-samples an existing (or reference) stack along z, recomputes a target
descriptor at each budget, and reports the convergence curve.

This convergence analysis is the empirical foundation for *cost-aware,
autonomous acquisition*: a policy that decides, on the fly, how many sections to
mill in order to reach a target uncertainty on a descriptor rather than
acquiring a fixed, conservative number. The active policy itself is on the
roadmap; the analysis that a policy needs is implemented and runnable today.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from ..core import Volume


@dataclass
class ConvergenceResult:
    """Descriptor value versus number of slices retained."""

    n_slices: List[int]
    values: List[float]
    reference_value: float
    descriptor: str

    def relative_errors(self) -> List[float]:
        ref = self.reference_value or 1e-12
        return [abs(v - self.reference_value) / abs(ref) for v in self.values]

    def slices_for_tolerance(self, tol: float) -> Optional[int]:
        """Smallest slice budget whose relative error stays within ``tol``.

        Scans from the largest budget downward and returns the smallest budget
        such that it and all larger budgets are within tolerance.
        """
        errs = self.relative_errors()
        pairs = sorted(zip(self.n_slices, errs))
        answer = None
        for n, e in reversed(pairs):
            if e <= tol:
                answer = n
            else:
                break
        return answer

    def to_dict(self) -> Dict[str, object]:
        return {
            "descriptor": self.descriptor,
            "reference_value": self.reference_value,
            "n_slices": self.n_slices,
            "values": self.values,
            "relative_errors": self.relative_errors(),
        }


def _subsample_z(volume: Volume, n: int) -> Volume:
    """Evenly retain ``n`` slices along z, rescaling z spacing accordingly."""
    nz = volume.n_slices
    idx = np.linspace(0, nz - 1, n).round().astype(int)
    idx = np.unique(idx)
    dz, dy, dx = volume.spacing
    # Effective spacing grows because slices are farther apart.
    new_dz = dz * (nz - 1) / (len(idx) - 1) if len(idx) > 1 else dz
    sub = Volume(
        data=volume.data[idx],
        spacing=(new_dz, dy, dx),
        units=volume.units,
        metadata={**volume.metadata, "subsampled_from": nz},
    )
    return sub


def convergence_study(
    volume: Volume,
    segmenter: Callable[[Volume], np.ndarray],
    descriptor: Callable[[np.ndarray, tuple], float],
    budgets: Optional[Sequence[int]] = None,
    descriptor_name: str = "descriptor",
) -> ConvergenceResult:
    """Measure a descriptor as a function of slice budget.

    Parameters
    ----------
    volume:
        The reference (fully sampled) stack.
    segmenter:
        Callable mapping a :class:`~altea.core.Volume` to a binary mask.
    descriptor:
        Callable mapping ``(mask, spacing)`` to a scalar (e.g. porosity).
    budgets:
        Slice counts to evaluate. Defaults to a geometric-ish sweep up to the
        full stack.
    """
    nz = volume.n_slices
    if budgets is None:
        budgets = sorted({
            max(2, int(round(f * nz)))
            for f in (0.1, 0.2, 0.3, 0.5, 0.7, 1.0)
        })

    ref_mask = segmenter(volume)
    ref_value = descriptor(ref_mask, volume.spacing)

    ns: List[int] = []
    vals: List[float] = []
    for b in budgets:
        b = min(b, nz)
        sub = _subsample_z(volume, b)
        mask = segmenter(sub)
        vals.append(descriptor(mask, sub.spacing))
        ns.append(sub.n_slices)

    return ConvergenceResult(
        n_slices=ns,
        values=vals,
        reference_value=ref_value,
        descriptor=descriptor_name,
    )

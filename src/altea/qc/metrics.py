"""Automated quality control for tomographic slices.

This module replaces the manual curation step in which an operator inspects
500-600 acquired slices and keeps the 300-400 usable ones, discarding sections
degraded by drift, blur, charging or curtaining. Each slice receives a set of
interpretable, physically-motivated scores; a reproducible, config-driven rule
then flags the slices to drop. Because the thresholds live in configuration and
the decision is deterministic, the same input always yields the same curated
stack -- and the reasons for every rejection are recorded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np
from scipy import ndimage as ndi
from skimage.registration import phase_cross_correlation


# --------------------------------------------------------------------------
# Per-slice metrics
# --------------------------------------------------------------------------
def sharpness(slice_2d: np.ndarray) -> float:
    """Focus/sharpness via the variance of the Laplacian.

    Blurred slices (defocus, redeposition) have a markedly lower value.
    """
    lap = ndi.laplace(slice_2d.astype(np.float32))
    return float(lap.var())


def brightness_stats(slice_2d: np.ndarray) -> tuple[float, float]:
    """Return the mean and standard deviation of slice intensity."""
    s = slice_2d.astype(np.float32)
    return float(s.mean()), float(s.std())


def curtaining_score(slice_2d: np.ndarray) -> float:
    """Estimate vertical-streak (curtaining) contamination.

    Curtaining produces stripes that are coherent along one image axis. We
    compare the energy of the column-averaged profile to the overall gradient
    energy; a high ratio indicates strong streaking.
    """
    s = slice_2d.astype(np.float32)
    col_profile = s.mean(axis=0)  # average over rows -> 1-D along columns
    col_var = np.var(np.diff(col_profile))
    gx = np.diff(s, axis=1)
    total = np.var(gx) + 1e-8
    return float(col_var / total)


def drift_shift(prev_2d: np.ndarray, slice_2d: np.ndarray) -> float:
    """Magnitude of the rigid shift between consecutive slices, in pixels.

    Large inter-slice shifts indicate stage drift or a mechanical jump.
    """
    shift, _, _ = phase_cross_correlation(
        prev_2d.astype(np.float32),
        slice_2d.astype(np.float32),
        upsample_factor=4,
        normalization=None,
    )
    return float(np.hypot(*shift))


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------
@dataclass
class SliceQC:
    """Quality metrics and verdict for a single slice."""

    index: int
    sharpness: float
    mean_intensity: float
    std_intensity: float
    curtaining: float
    drift: float
    keep: bool = True
    reasons: List[str] = field(default_factory=list)


@dataclass
class QCReport:
    """QC results for a whole stack."""

    slices: List[SliceQC]

    @property
    def kept_indices(self) -> List[int]:
        return [s.index for s in self.slices if s.keep]

    @property
    def dropped_indices(self) -> List[int]:
        return [s.index for s in self.slices if not s.keep]

    def summary(self) -> Dict[str, object]:
        n = len(self.slices)
        kept = len(self.kept_indices)
        reason_counts: Dict[str, int] = {}
        for s in self.slices:
            for r in s.reasons:
                reason_counts[r] = reason_counts.get(r, 0) + 1
        return {
            "n_slices": n,
            "n_kept": kept,
            "n_dropped": n - kept,
            "keep_fraction": kept / n if n else 0.0,
            "drop_reasons": reason_counts,
        }

    def to_records(self) -> List[Dict[str, object]]:
        return [asdict(s) for s in self.slices]


# --------------------------------------------------------------------------
# Assessment + selection
# --------------------------------------------------------------------------
def assess_stack(volume) -> List[SliceQC]:
    """Compute per-slice QC metrics for every slice in a volume."""
    data = volume.data
    nz = data.shape[0]
    records: List[SliceQC] = []
    prev = None
    for z in range(nz):
        sl = data[z]
        mean_i, std_i = brightness_stats(sl)
        drift = 0.0 if prev is None else drift_shift(prev, sl)
        records.append(
            SliceQC(
                index=z,
                sharpness=sharpness(sl),
                mean_intensity=mean_i,
                std_intensity=std_i,
                curtaining=curtaining_score(sl),
                drift=drift,
            )
        )
        prev = sl
    return records


def select_slices(
    records: List[SliceQC],
    *,
    sharpness_z: float = -2.5,
    brightness_z: float = 3.0,
    drift_px: Optional[float] = None,
    drift_z: float = 3.0,
    curtaining_z: float = 3.0,
    min_keep_fraction: float = 0.0,
) -> QCReport:
    """Flag slices to discard using robust, config-driven thresholds.

    Thresholds are expressed as robust z-scores (deviations from the median in
    units of the median absolute deviation), so they adapt to each stack rather
    than relying on hand-tuned absolute values. A slice is dropped if it is:

    * far *below* the typical sharpness (blurred), or
    * far from the typical brightness (charging / detector drift), or
    * shifted far more than its neighbours (drift / jump), or
    * strongly streaked (curtaining).

    Parameters
    ----------
    drift_px:
        Optional absolute drift ceiling in pixels. If given, it is applied in
        addition to the robust ``drift_z`` rule.
    min_keep_fraction:
        Safety floor. If the rules would keep fewer than this fraction of
        slices, only the worst-scoring slices are dropped until the floor is
        reached (prevents pathological over-rejection).
    """
    if not records:
        return QCReport(slices=[])

    def robust_z(values: np.ndarray) -> np.ndarray:
        med = np.median(values)
        mad = np.median(np.abs(values - med)) or 1e-8
        return (values - med) / (1.4826 * mad)

    sharp = np.array([r.sharpness for r in records])
    bright = np.array([r.mean_intensity for r in records])
    drift = np.array([r.drift for r in records])
    curt = np.array([r.curtaining for r in records])

    zs_sharp = robust_z(sharp)
    zs_bright = robust_z(bright)
    zs_drift = robust_z(drift)
    zs_curt = robust_z(curt)

    for i, r in enumerate(records):
        r.keep = True
        r.reasons = []
        if zs_sharp[i] < sharpness_z:
            r.reasons.append("blur")
        if abs(zs_bright[i]) > brightness_z:
            r.reasons.append("charging")
        if zs_drift[i] > drift_z:
            r.reasons.append("drift")
        if drift_px is not None and r.drift > drift_px:
            if "drift" not in r.reasons:
                r.reasons.append("drift")
        if zs_curt[i] > curtaining_z:
            r.reasons.append("curtaining")
        r.keep = len(r.reasons) == 0

    # Enforce the safety floor on keep fraction.
    n = len(records)
    kept = sum(r.keep for r in records)
    if min_keep_fraction > 0 and kept / n < min_keep_fraction:
        # Rank slices by a combined severity; restore the least-bad ones.
        severity = (
            np.maximum(0, -zs_sharp)
            + np.abs(zs_bright)
            + np.maximum(0, zs_drift)
            + np.maximum(0, zs_curt)
        )
        order = np.argsort(severity)  # least severe first
        target = int(np.ceil(min_keep_fraction * n))
        for idx in order:
            if sum(r.keep for r in records) >= target:
                break
            if not records[idx].keep:
                records[idx].keep = True
                records[idx].reasons.append("restored_by_floor")

    return QCReport(slices=records)


def run_qc(volume, **selection_kwargs) -> QCReport:
    """Convenience: assess a volume and select slices in one call."""
    records = assess_stack(volume)
    return select_slices(records, **selection_kwargs)


def apply_report(volume, report: QCReport):
    """Return a new volume containing only the kept slices."""
    keep = report.kept_indices
    if not keep:
        raise ValueError("QC report keeps no slices.")
    return volume.with_data(volume.data[keep])

"""Test suite for ALTEA.

Tests validate scientific correctness on synthetic data with known ground truth:
segmentation should recover the prescribed porosity, QC should flag injected
defects, and tortuosity must exceed 1. They also check reproducibility (equal
inputs give equal provenance hashes) and the plugin registry.
"""
import numpy as np
import pytest

from altea import Pipeline, Volume
from altea.datasets import add_acquisition_artifacts, make_porous_volume
from altea import morphometry, qc, segment


@pytest.fixture(scope="module")
def clean_volume():
    vol, gt = make_porous_volume(shape=(48, 96, 96), porosity=0.35, seed=0)
    return vol, gt


# -- core ------------------------------------------------------------------
def test_volume_requires_3d():
    with pytest.raises(ValueError):
        Volume(np.zeros((4, 4)))


def test_voxel_volume_and_anisotropy():
    v = Volume(np.zeros((2, 2, 2)), spacing=(10.0, 5.0, 5.0))
    assert v.voxel_volume == 250.0
    assert v.anisotropy == 2.0


def test_hash_is_deterministic(clean_volume):
    vol, _ = clean_volume
    assert vol.hash() == vol.hash()
    assert vol.with_data(vol.data + 1).hash() != vol.hash()


# -- qc --------------------------------------------------------------------
def test_qc_flags_injected_defects(clean_volume):
    vol, _ = clean_volume
    raw = add_acquisition_artifacts(
        vol, blur_slices=(10,), charge_slices=(20,), seed=1
    )
    report = qc.run_qc(raw)
    dropped = set(report.dropped_indices)
    # The charged slice (strong brightness outlier) must be caught.
    assert 20 in dropped
    assert report.summary()["n_dropped"] >= 1


def test_qc_keep_fraction_floor(clean_volume):
    vol, _ = clean_volume
    report = qc.run_qc(vol, min_keep_fraction=0.9)
    assert report.summary()["keep_fraction"] >= 0.9


# -- segmentation ----------------------------------------------------------
def test_registry_contains_expected_backends():
    names = segment.available_backends()
    for expected in ("otsu", "watershed", "pixel_rf", "unet"):
        assert expected in names


def test_otsu_recovers_porosity(clean_volume):
    vol, gt = clean_volume
    backend = segment.get_backend("otsu", invert=True, mode="global")
    mask = backend.predict(vol)
    assert abs(mask.mean() - gt.mean()) < 0.05


def test_pixel_rf_trains_and_predicts(clean_volume):
    vol, gt = clean_volume
    # Sparse labels: annotate two slices fully, rest ignored (-1).
    labels = np.full(vol.shape, -1, dtype=np.int32)
    for z in (0, vol.n_slices - 1):
        labels[z] = gt[z].astype(np.int32)
    backend = segment.get_backend("pixel_rf", n_estimators=30, random_state=0)
    mask = backend.fit_predict(vol, labels).astype(bool)
    # Learned classifier should also approach the true porosity.
    assert abs(mask.mean() - gt.mean()) < 0.08


# -- morphometry -----------------------------------------------------------
def test_morphometry_on_ground_truth(clean_volume):
    vol, gt = clean_volume
    report = morphometry.analyze_volume(vol, gt, compute_tortuosity=True)
    assert abs(report.porosity - gt.mean()) < 1e-6
    assert report.specific_surface_area > 0
    # Tortuosity is >= 1 by definition where the phase percolates.
    for axis, t in report.tortuosity.items():
        if not np.isnan(t):
            assert t >= 1.0 - 1e-6


def test_connectivity_percolation():
    # A straight open channel percolates along z but not necessarily elsewhere.
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[:, 4:6, 4:6] = True
    conn = morphometry.connectivity(mask)
    assert conn["percolates_z"] is True
    assert conn["n_components"] == 1


# -- pipeline & reproducibility -------------------------------------------
def test_pipeline_end_to_end(clean_volume):
    vol, gt = clean_volume
    raw = add_acquisition_artifacts(vol, charge_slices=(15,), seed=2)
    results = Pipeline().run(raw)
    assert "morphometry" in results
    assert abs(results["morphometry"].porosity - gt.mean()) < 0.06
    prov = results["provenance"]
    assert prov.input_hash == raw.hash()
    assert [s.name for s in prov.stages][:2] == ["qc", "align"]


def test_pipeline_is_reproducible(clean_volume):
    vol, _ = clean_volume
    r1 = Pipeline().run(vol)
    r2 = Pipeline().run(vol)
    assert r1["mask"].sum() == r2["mask"].sum()
    assert (
        r1["provenance"].stages[-1].metrics["porosity"]
        == r2["provenance"].stages[-1].metrics["porosity"]
    )

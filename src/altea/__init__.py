"""ALTEA: Autonomous Learning for Tomographic Ensembles and Attributes.

A reproducible, provenance-tracked pipeline for automated quality control,
segmentation and 3-D morphometry of tomographic image stacks (e.g. FIB-SEM),
with a focus on porous and heterogeneous materials.

Typical use::

    from altea import Pipeline
    from altea.datasets import make_porous_volume, add_acquisition_artifacts

    clean, _ = make_porous_volume()
    raw = add_acquisition_artifacts(clean, blur_slices=(10,), charge_slices=(20,))
    results = Pipeline().run(raw, output_dir="runs/demo")
    print(results["morphometry"].porosity)
"""
from __future__ import annotations

from .core import Volume
from .pipeline import Pipeline, load_config
from .provenance import ProvenanceRecord

__all__ = ["Volume", "Pipeline", "load_config", "ProvenanceRecord", "__version__"]

try:  # keep in sync with pyproject
    from importlib.metadata import version as _v

    __version__ = _v("altea")
except Exception:  # pragma: no cover
    __version__ = "0.1.0"

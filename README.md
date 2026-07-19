# ALTEA

**Autonomous Learning for Tomographic Ensembles and Attributes**

A reproducible, provenance-tracked Python pipeline for automated quality
control, segmentation and 3-D morphometry of tomographic image stacks such as
FIB-SEM. Built with porous and heterogeneous materials in mind (MOFs, battery
electrodes, catalysts, membranes, rock), but general to any two-phase or
multi-phase volumetric acquisition.

[![CI](https://github.com/jorgebravoabad/altea/actions/workflows/ci.yml/badge.svg)](https://github.com/jorgebravoabad/altea/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/altea.svg)](https://pypi.org/project/altea/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21442516.svg)](https://doi.org/10.5281/zenodo.21442516)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Why

Analysing FIB-SEM tomography today typically involves two costly, poorly
reproducible steps: an operator manually discards a large fraction of acquired
slices (e.g. 500–600 acquired, 300–400 kept) by visual inspection, and the
image treatment is tuned by eye per sample "like Photoshop", with no single
procedure that applies across samples. ALTEA turns both into deterministic,
config-driven, versioned operations, and records exactly what was done to every
volume.

ALTEA is a reproducible **orchestration layer**, not a single model. Every stage
is explicit, every parameter lives in a config file, and every run emits a
provenance record (software and dependency versions, input data hash, per-stage
parameters and metrics). The same input always yields the same result — and you
can prove it.

## Pipeline

```
load → quality control → drift correction → preprocessing → segmentation → morphometry
```

| Stage | What it does |
|-------|--------------|
| **io** | Load FIB-SEM stacks (multi-page TIFF or slice directories) with voxel spacing |
| **qc** | Per-slice sharpness / brightness / drift / curtaining scores; reproducible, threshold-driven slice selection (replaces manual curation) |
| **align** | Rigid drift correction by phase cross-correlation |
| **preprocess** | Deterministic denoising and contrast normalization — every parameter recorded |
| **segment** | Pluggable backends: classical (Otsu, watershed) and learned (random-forest pixel classifier; optional deep U-Net) |
| **morphometry** | Porosity, specific surface area, pore-size distribution, connectivity/percolation, geometric tortuosity — all voxel-size-aware |
| **acquire** | Convergence analysis: how few slices suffice for a target accuracy (basis for cost-aware acquisition) |

## Install

```bash
pip install altea            # core
pip install "altea[deep]"    # + optional deep-learning segmentation backends
pip install "altea[dev]"     # + test / lint tooling
```

## Quickstart

No data required — run the synthetic demo:

```bash
altea demo --output runs/demo
```

Or on your own stack:

```bash
altea run --input stack.tif --config configs/fibsem_default.yaml --output runs/sample1
```

In Python:

```python
from altea import Pipeline
from altea.datasets import make_porous_volume, add_acquisition_artifacts

clean, ground_truth = make_porous_volume(porosity=0.35)
raw = add_acquisition_artifacts(clean, blur_slices=(8,), charge_slices=(15,))

results = Pipeline.from_yaml("configs/fibsem_default.yaml").run(raw, output_dir="runs/demo")

m = results["morphometry"]
print(m.porosity, m.specific_surface_area, m.tortuosity)
print(results["qc_report"].summary())      # which slices were dropped, and why
```

## Segmentation backends

Backends share one interface and self-register, so switching is a one-line
config change:

```yaml
segment:
  backend: pixel_rf      # otsu | watershed | pixel_rf | unet
  params: {sigmas: [1, 2, 4], n_estimators: 200}
```

Add your own by subclassing `SegmentationBackend` and decorating with
`@register_backend`. Nothing else in the pipeline changes.

## Reproducibility

Every run writes `provenance.json`:

```json
{
  "altea_version": "0.1.0",
  "dependency_versions": {"numpy": "...", "scikit-image": "..."},
  "input_hash": "sha256:...",
  "config": {...},
  "stages": [{"name": "qc", "params": {...}, "metrics": {...}}, ...]
}
```

## Roadmap

- **Cost-aware autonomous acquisition.** The `acquire` module already quantifies
  the accuracy-vs-slice-count trade-off. The next step is an active policy that
  decides on the fly how many sections to acquire to reach a target uncertainty,
  reducing destructive beam time.
- Deep segmentation backends (2-D U-Net / nnU-Net wrapper) under `altea[deep]`.
- Sparse-view reconstruction of discarded slices.

## Status

Alpha. Interfaces may change before 1.0.

## Citation

If you use ALTEA in your research, please cite the archived software:

> Bravo-Abad, J. (2026). *ALTEA: Autonomous Learning for Tomographic Ensembles
> and Attributes* (v0.1.0). Zenodo. https://doi.org/10.5281/zenodo.21442516

```bibtex
@software{bravoabad_altea_2026,
  author    = {Bravo-Abad, Jorge},
  title     = {{ALTEA: Autonomous Learning for Tomographic Ensembles
               and Attributes}},
  year      = {2026},
  version   = {0.1.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21442516},
  url       = {https://doi.org/10.5281/zenodo.21442516}
}
```

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE).

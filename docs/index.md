# ALTEA

**Autonomous Learning for Tomographic Ensembles and Attributes**

A reproducible, provenance-tracked Python pipeline for automated quality
control, segmentation and 3-D morphometry of tomographic image stacks such as
FIB-SEM. Built with porous and heterogeneous materials in mind (MOFs, battery
electrodes, catalysts, membranes, rock), but general to any two-phase or
multi-phase volumetric acquisition.

```{admonition} At a glance
:class: tip

- **Automated quality control** replaces manual slice curation, and records *why* each slice was dropped.
- **Deterministic preprocessing** — every filter parameter is explicit and logged, not tuned by eye.
- **Pluggable segmentation** — classical, learned, or deep backends behind one interface.
- **Voxel-size-aware morphometry** — porosity, surface area, pore-size distribution, tortuosity in physical units.
- **Provenance on every run** — versions, input hash, per-stage parameters and metrics.
```

## Why ALTEA

Analysing FIB-SEM tomography today typically involves two costly, poorly
reproducible steps. An operator manually discards a large fraction of acquired
slices by visual inspection, and the image treatment is tuned by eye per sample
"like Photoshop", with no single procedure that transfers across samples.

ALTEA turns both into deterministic, config-driven, versioned operations, and
records exactly what was done to every volume. It is a reproducible
**orchestration layer**, not a single model: a run is fully described by its
configuration plus the hash of its input.

## Install

```bash
pip install altea            # core
pip install "altea[deep]"    # + optional deep-learning segmentation backends
pip install "altea[dev]"     # + test and lint tooling
```

## Thirty-second example

```python
from altea import Pipeline
from altea.datasets import make_porous_volume, add_acquisition_artifacts

clean, ground_truth = make_porous_volume(porosity=0.35)
raw = add_acquisition_artifacts(clean, blur_slices=(8,), charge_slices=(15,))

results = Pipeline().run(raw, output_dir="runs/demo")

m = results["morphometry"]
print(m.porosity, m.specific_surface_area, m.tortuosity)
print(results["qc_report"].summary())   # which slices were dropped, and why
```

Or from the command line, with no data required:

```bash
altea demo --output runs/demo
```

```{toctree}
:maxdepth: 2
:caption: Getting started
:hidden:

installation
quickstart
configuration
```

```{toctree}
:maxdepth: 2
:caption: User guide
:hidden:

pipeline
segmentation
morphometry
provenance
acquisition
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

api/index
architecture
contributing
citing
```

## Citing

If you use ALTEA in your research, please cite the archived software — see
{doc}`citing`.

## License

MIT. See the [LICENSE](https://github.com/jorgebravoabad/altea/blob/main/LICENSE)
file.

# Architecture

ALTEA is organized as a set of small, single-responsibility modules coordinated
by a configuration-driven orchestrator. The design goal is that a run is fully
described by its configuration plus the hash of its input, so results are
reproducible and auditable.

## Data model

Everything flows through `altea.core.Volume`: a 3-D array in `(z, y, x)` order
plus physical voxel `spacing` and free-form `metadata`. Carrying spacing with
the data is what keeps every physical descriptor (surface area, pore diameter,
tortuosity) correct under the anisotropic voxels typical of FIB-SEM.

## Stages

Each stage is an independent module with a narrow interface:

- `io` — load/save stacks (multi-page TIFF or slice directories).
- `qc` — per-slice metrics (`sharpness`, `brightness`, `drift`, `curtaining`)
  and a robust, threshold-driven `select_slices` that reproduces manual
  curation deterministically and records *why* each slice was dropped.
- `align` — rigid drift correction by phase cross-correlation.
- `preprocess` — deterministic `denoise` and `normalize_contrast`; every
  parameter is explicit and logged.
- `segment` — a `SegmentationBackend` interface plus a registry. Backends
  (`otsu`, `watershed`, `pixel_rf`, `unet`) self-register and are selected by
  name from config.
- `morphometry` — `analyze` returns porosity, specific surface area, pore-size
  distribution, connectivity/percolation and geometric tortuosity.
- `acquire` — `convergence_study` quantifies descriptor accuracy vs slice
  budget; the foundation for cost-aware acquisition.
- `viz` — deterministic figures.

## Orchestration and provenance

`pipeline.Pipeline` reads a YAML config, runs the enabled stages in order, and
builds a `ProvenanceRecord`: ALTEA and dependency versions, platform, optional
git commit, the resolved config, the input hash, and per-stage parameters,
metrics, timing and I/O hashes. It is written as `provenance.json` next to the
outputs.

## Extension points

- **New segmentation backend:** subclass `SegmentationBackend`, implement
  `predict` (and optionally `fit`), decorate with `@register_backend`. No
  pipeline or schema change is needed.
- **New descriptor:** add a function to `morphometry` and surface it in
  `MorphometryReport`.
- **New stage:** add a module and a block in `Pipeline.run`, wrapping the call
  in `self._timed` so it is recorded in provenance.

## Design choices worth noting

- **2-D slice-wise by default.** FIB-SEM stacks are usually anisotropic, and
  2-D processing needs far fewer annotations. 3-D variants are opt-in.
- **Robust z-score thresholds in QC.** Thresholds are expressed relative to the
  per-stack median/MAD, so they adapt to each dataset instead of relying on
  brittle absolute values.
- **Reproducibility over cleverness.** Fixed random seeds, headless plotting,
  content hashing and explicit config are deliberate: the framework's value is
  that the same input always yields the same, fully-documented output.

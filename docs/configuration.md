# Configuration

A run is fully described by its configuration plus the hash of its input. The
configuration is a YAML file; anything you do not set falls back to a documented
default, and the *resolved* configuration (defaults included) is written into
the provenance record.

## A complete example

```yaml
qc:
  enabled: true
  params:
    sharpness_z: -2.5        # drop slices far below typical sharpness (blur)
    brightness_z: 3.0        # drop brightness outliers (charging)
    drift_z: 3.0             # drop abnormally large inter-slice shifts
    curtaining_z: 3.0        # drop strongly streaked slices
    min_keep_fraction: 0.5   # safety floor against over-rejection

align:
  enabled: true
  upsample_factor: 10        # sub-pixel drift correction

preprocess:
  enabled: true
  denoise:
    method: median           # median | gaussian | bilateral | nlmeans
    size: 3
  normalize:
    method: percentile       # percentile | clahe
    low_percentile: 1.0
    high_percentile: 99.0

segment:
  backend: otsu              # otsu | watershed | pixel_rf | unet
  params:
    invert: true             # pore phase is darker than the solid
    mode: global

morphometry:
  enabled: true
  compute_tortuosity: true
  psd_bins: 20
```

Load it with `Pipeline.from_yaml("path.yaml")`, or pass a dict to
`Pipeline(config)`.

## Quality control

Thresholds are **robust z-scores**: deviations from the per-stack median in
units of the median absolute deviation. Expressing them this way lets one
configuration adapt across acquisitions instead of relying on brittle absolute
values.

| Key | Default | Meaning |
|-----|---------|---------|
| `sharpness_z` | `-2.5` | Drop if sharpness is this many robust z below the median. More negative = more permissive. |
| `brightness_z` | `3.0` | Drop if mean intensity deviates this far in either direction (charging). |
| `drift_z` | `3.0` | Drop if the inter-slice shift is this far above typical. |
| `drift_px` | `None` | Optional absolute drift ceiling in pixels, applied in addition. |
| `curtaining_z` | `3.0` | Drop if vertical streaking is this far above typical. |
| `min_keep_fraction` | `0.0` | Floor on the fraction kept; least-severe slices are restored if the rules would over-reject. |

```{admonition} Tuning sharpness_z
:class: note

The default of `-2.5` is deliberately conservative: it removes strong artefacts
without false positives, but can miss subtle defocus. If you know your stack has
blurred sections that are being kept, relax it toward `-2.0` or `-1.5` and check
the QC panel. Because the threshold is recorded in the provenance, your
operating point is auditable rather than a private judgement call.
```

## Alignment

| Key | Default | Meaning |
|-----|---------|---------|
| `upsample_factor` | `10` | Sub-pixel precision of phase cross-correlation. Higher is finer but slower. |

## Preprocessing

Denoising methods: `median` (fast, edge-preserving, good default), `gaussian`,
`bilateral` (edge-preserving, slower), `nlmeans` (best quality, slowest).

Normalization methods: `percentile` computes **one mapping over the whole
volume**, so all slices share it — usually what you want for a stack.
`clahe` equalizes slice-wise and can amplify noise, but helps when illumination
drifts through the stack.

## Segmentation

```yaml
segment:
  backend: pixel_rf
  phase_label: 1                      # which label is the phase of interest
  labels: data/sparse_labels.tif      # required for supervised backends
  params:
    sigmas: [1.0, 2.0, 4.0]
    n_estimators: 200
    random_state: 0
```

See {doc}`segmentation` for the full backend list and how to add your own.

## Morphometry

| Key | Default | Meaning |
|-----|---------|---------|
| `compute_tortuosity` | `true` | Geodesic tortuosity per axis. The most expensive descriptor. |
| `psd_bins` | `20` | Bins in the pore-size distribution histogram. |

```{tip}
On large stacks, set `compute_tortuosity: false` for a fast first pass, then
enable it on a representative subvolume.
```

## Disabling stages

Every stage takes `enabled: false`. A segmentation-only run:

```yaml
qc: {enabled: false}
align: {enabled: false}
preprocess: {enabled: false}
segment: {backend: otsu, params: {invert: true}}
morphometry: {enabled: true, compute_tortuosity: false}
```

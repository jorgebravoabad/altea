# The pipeline

ALTEA runs five independent stages in order:

```
load → quality control → drift correction → preprocessing → segmentation → morphometry
```

Each stage is a pure function of its input and its explicit parameters. The
runner times every stage, records its parameters and metrics, and hashes its
input and output.

## Quality control

Replaces the manual curation step in which an operator inspects hundreds of
acquired slices and keeps the usable ones. Four interpretable scores are
computed per slice:

| Metric | Detects | Definition |
|--------|---------|------------|
| `sharpness` | defocus, redeposition | variance of the Laplacian |
| `mean_intensity` | charging, detector drift | slice mean |
| `curtaining` | milling streaks | energy of the column-coherent profile |
| `drift` | stage drift, jumps | phase-correlation shift vs the previous slice |

Slices are flagged by robust z-score thresholds, and **each rejection carries a
reason**:

```python
from altea import qc

report = qc.run_qc(volume, sharpness_z=-2.0, min_keep_fraction=0.5)
print(report.summary())
curated = qc.apply_report(volume, report)
```

## Drift correction

Estimates the cumulative `(y, x)` shift of each slice by phase
cross-correlation against its predecessor, then resamples onto a common frame.
The shift array is returned for provenance.

```python
from altea import align

aligned, shifts = align.correct_drift(volume, upsample_factor=10)
print(f"max shift: {abs(shifts).max():.2f} px")
```

## Preprocessing

Denoising and contrast normalization, with every parameter explicit.

```python
from altea import preprocess

v = preprocess.denoise(volume, method="median", size=3)
v = preprocess.normalize_contrast(v, method="percentile",
                                  low_percentile=1.0, high_percentile=99.0)
```

## Segmentation

See {doc}`segmentation`.

## Morphometry

See {doc}`morphometry`.

## Composing stages yourself

The `Pipeline` is a convenience. Every stage is importable and usable directly,
which is useful for exploratory work:

```python
from altea import qc, align, preprocess, morphometry
from altea.segment import get_backend

report = qc.run_qc(raw)
v = qc.apply_report(raw, report)
v, shifts = align.correct_drift(v)
v = preprocess.denoise(v, method="median", size=3)
mask = get_backend("otsu", invert=True).predict(v)
m = morphometry.analyze_volume(v, mask)
```

```{note}
Composing stages by hand skips the provenance record. For results you intend to
publish, run through `Pipeline` so the run is documented.
```

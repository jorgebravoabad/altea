# Quickstart

This page takes you from a raw stack to quantitative descriptors.

## 1. Load a stack

ALTEA reads multi-page TIFFs and directories of single-page TIFFs. Voxel
spacing is carried with the data, in `(z, y, x)` order, because every physical
descriptor depends on it.

```python
from altea import io

volume = io.load_stack("data/sample1.tif", spacing=(20.0, 5.0, 5.0), units="nm")
print(volume)          # Volume(shape=(400, 1024, 1024), spacing=(20.0, 5.0, 5.0) nm)
print(volume.anisotropy)   # 4.0 -> anisotropic, slice-wise processing preferred
```

```{important}
Getting `spacing` right matters. Surface area, pore diameters and tortuosity are
all reported in physical units derived from it. FIB-SEM stacks are usually
anisotropic: the sectioning step along `z` is coarser than the in-plane pixel
size.
```

## 2. Run the pipeline

```python
from altea import Pipeline

pipe = Pipeline.from_yaml("configs/fibsem_default.yaml")
results = pipe.run(volume, output_dir="runs/sample1")
```

The `output_dir` receives the segmented mask, a `morphometry.json` with all
descriptors, and a `provenance.json` recording exactly what was done.

## 3. Inspect the results

```python
qc = results["qc_report"]
print(qc.summary())
# {'n_slices': 400, 'n_kept': 383, 'n_dropped': 17,
#  'keep_fraction': 0.957, 'drop_reasons': {'drift': 9, 'charging': 5, 'blur': 3}}

print(qc.dropped_indices)     # exactly which slices went, and
for s in qc.slices:
    if not s.keep:
        print(s.index, s.reasons)   # ... exactly why
```

```python
m = results["morphometry"]
print(f"porosity            {m.porosity:.3f}")
print(f"specific surface    {m.specific_surface_area:.4g} 1/{m.units}")
print(f"mean pore diameter  {m.psd['mean']:.1f} {m.units}")
print(f"tortuosity (z,y,x)  {m.tortuosity}")
print(f"percolates          {m.connectivity['percolates_any']}")
```

## 4. Make figures

```python
from altea import viz

viz.orthoslices(volume, path="figs/ortho.png")
viz.qc_panel(results["qc_report"], path="figs/qc.png")
viz.psd_plot(m, path="figs/psd.png")
```

Figures are deterministic pure functions of their inputs, so the panels in a
paper can be regenerated exactly from saved outputs.

## Running from the command line

```bash
altea run --input data/sample1.tif --config configs/fibsem_default.yaml --output runs/sample1
```

## Next steps

- {doc}`configuration` — every knob, and what it does
- {doc}`segmentation` — choosing and adding backends
- {doc}`provenance` — what gets recorded and how to use it

# Morphometry

Given a binary mask and the voxel spacing, ALTEA computes the descriptors that
constitute the quantitative output. All respect anisotropic spacing and are
reported in physical units.

```python
from altea import morphometry

report = morphometry.analyze_volume(volume, mask, compute_tortuosity=True)
print(report.to_dict())
```

## Descriptors

### Porosity

Volume fraction of the phase. The most robust descriptor, and the one that
converges with the fewest slices.

```python
morphometry.porosity(mask)   # 0.347
```

### Specific surface area

Interfacial area per unit total volume, in units of `1/length`. The interface is
meshed with marching cubes, respecting anisotropic spacing, and the area divided
by the total physical volume.

```python
morphometry.specific_surface_area(mask, spacing=(20.0, 5.0, 5.0))
```

```{warning}
Surface area is sensitive to voxel resolution and to noise in the segmentation:
a rougher segmentation reports more area. Compare values only across
acquisitions with matched resolution and processing.
```

### Pore-size distribution

Distance-transform granulometry: each pore voxel is assigned the diameter of the
largest sphere that fits within the phase and contains it — the local-thickness
definition.

```python
psd = morphometry.pore_size_distribution(mask, spacing, n_bins=20)
psd["mean"], psd["median"], psd["bin_centers"], psd["pdf"]
```

### Connectivity and percolation

```python
conn = morphometry.connectivity(mask)
# {'n_components': 12, 'largest_fraction': 0.981,
#  'percolates_z': True, 'percolates_y': True, 'percolates_x': False,
#  'percolates_any': True}
```

### Geometric tortuosity

Mean geodesic path length through the percolating phase from entry face to exit
face, divided by the straight-line domain length. Always ≥ 1. Returns `nan` if
the phase does not percolate along that axis.

```python
morphometry.geometric_tortuosity(mask, spacing, axis=0)   # 1.23
```

## Performance

Tortuosity and the pore-size distribution are the expensive descriptors — both
scale poorly to a full-resolution stack in the current dependency-light
implementations. Practical strategies:

- Analyse a **representative subvolume** rather than the full stack.
- Set `compute_tortuosity=False` for a fast first pass.
- For heavy analysis, pass the segmented mask to a specialised library such as
  [PoreSpy](https://porespy.org) or [TauFactor](https://github.com/tldr-group/taufactor).

ALTEA's contribution is the reproducible production of the segmented volume plus
a first set of descriptors; it does not aim to replace dedicated porous-media
analysis packages.

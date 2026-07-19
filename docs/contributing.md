# Contributing

Contributions are welcome — bug reports, backends, descriptors and documentation
alike.

## Development setup

```bash
git clone https://github.com/jorgebravoabad/altea.git
cd altea
pip install -e ".[dev]"
pytest -q
```

## Adding a segmentation backend

The most common extension. Subclass `SegmentationBackend`, implement `predict`
(and `fit` if supervised), and register it:

```python
import numpy as np
from altea.segment import SegmentationBackend, register_backend

@register_backend
class MyBackend(SegmentationBackend):
    name = "my_backend"

    def predict(self, volume):
        return (volume.data > volume.data.mean()).astype(np.int32)
```

It is then selectable from configuration with no other changes:

```yaml
segment:
  backend: my_backend
```

## Adding a descriptor

Add a function to `altea.morphometry` that takes `(mask, spacing)` and returns a
scalar or dict in physical units, then surface it in `MorphometryReport`.

## Guidelines

- **Determinism.** Fix random seeds; equal inputs must give equal outputs.
- **Spacing awareness.** Any geometric quantity must respect anisotropic voxel
  spacing and report physical units.
- **Tests with ground truth.** Validate against synthetic data where the answer
  is known — see `altea.datasets`.
- **Docstrings.** NumPy style; they become the API reference automatically.

## Running the docs locally

```bash
pip install sphinx furo myst-parser sphinx-copybutton
sphinx-build -b html docs docs/_build/html
```

## Reporting issues

Open an issue at
<https://github.com/jorgebravoabad/altea/issues>. For analysis problems,
attaching the `provenance.json` from the run makes diagnosis far quicker.

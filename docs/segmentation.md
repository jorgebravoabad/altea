# Segmentation backends

All backends implement `altea.segment.base.SegmentationBackend`:

```python
class SegmentationBackend(ABC):
    name: str
    def fit(self, volume, labels=None): ...      # optional (learned backends)
    def predict(self, volume) -> np.ndarray: ...  # required
```

## Built-in backends

| name | type | notes |
|------|------|-------|
| `otsu` | classical, unsupervised | global or local threshold; strong two-phase baseline |
| `watershed` | classical, unsupervised | instance labels for touching objects |
| `pixel_rf` | learned, supervised | random-forest over multi-scale features; the open analog of Ilastik / Avizo-ML; trains from sparse annotations |
| `unet` | learned, deep (optional) | 2-D U-Net extension point; requires `altea[deep]` |

## Adding your own

```python
import numpy as np
from altea.segment import SegmentationBackend, register_backend

@register_backend
class MyBackend(SegmentationBackend):
    name = "my_backend"
    def predict(self, volume):
        return (volume.data > volume.data.mean()).astype(np.int32)
```

Select it from config:

```yaml
segment:
  backend: my_backend
```

## Reference U-Net skeleton (deep extra)

The `unet` backend accepts a pre-trained `model=` (any callable mapping a
`(1, 1, H, W)` tensor to per-class logits). A minimal 2-D U-Net can be trained
slice-wise on sparse annotations; see the `pixel_rf` backend for a
dependency-light learned baseline that needs no GPU.

# Installation

## Requirements

ALTEA requires **Python 3.9 or newer**. The core package depends only on the
standard scientific-Python stack: NumPy, SciPy, scikit-image, scikit-learn,
tifffile, PyYAML and Matplotlib.

## From PyPI

```bash
pip install altea
```

## Optional extras

| Extra | Install | Adds |
|-------|---------|------|
| `deep` | `pip install "altea[deep]"` | PyTorch, enabling deep segmentation backends |
| `dev`  | `pip install "altea[dev]"`  | pytest, coverage and ruff for development |

The deep-learning dependency is deliberately optional so the core installs
quickly in constrained environments, such as alongside instrument-control
software.

## From source

```bash
git clone https://github.com/jorgebravoabad/altea.git
cd altea
pip install -e ".[dev]"
```

## Verifying the installation

```bash
altea demo --output runs/demo
```

This generates a synthetic porous volume, injects acquisition artefacts, runs
the full pipeline and prints the recovered morphometry. It requires no external
data. You should see the measured porosity land close to the ground-truth value
of 0.350.

To run the test suite from a source checkout:

```bash
pytest -q
```

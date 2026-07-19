# Acquisition analysis

FIB-SEM acquisition is destructive and expensive: hours of instrument time per
sample, and the material is physically removed as it is imaged. Cost scales with
the number of slices milled. The `acquire` module quantifies what that cost
buys.

## The convergence study

Sub-sample an existing stack along `z`, recompute a descriptor at each budget,
and measure how the estimate converges.

```python
from altea.acquire import convergence_study
from altea.morphometry import porosity
from altea.segment import get_backend

otsu = get_backend("otsu", invert=True, mode="global")

conv = convergence_study(
    volume,
    segmenter=otsu.predict,
    descriptor=lambda mask, spacing: porosity(mask),
    descriptor_name="porosity",
)

print(conv.slices_for_tolerance(0.02))   # e.g. 16 of 80 slices
print(conv.relative_errors())
```

Plot it:

```python
from altea import viz
viz.convergence_plot(conv, tol=0.02, path="figs/convergence.png")
```

## Interpreting the result

On a synthetic porous volume, porosity converges quickly: in the reference
experiment, 16 of 80 slices sufficed for 2% relative error, and 8 for 5%.

```{important}
This applies to **porosity**, which averages over the whole stack and is the
most forgiving descriptor. Surface area and tortuosity depend on finer geometric
detail and require more slices. Run the convergence study on *your* descriptor
of interest rather than assuming the porosity result transfers.
```

## Toward cost-aware acquisition

The convergence curve is the empirical foundation for a policy that decides how
many sections to mill in order to reach a target uncertainty, instead of
acquiring a fixed, conservative number.

That active policy is on the roadmap; the analysis it requires is implemented
and runnable today. Practically, you can already use it to plan: run a
convergence study on a pilot stack, find the budget your target tolerance
requires, and size subsequent acquisitions accordingly.

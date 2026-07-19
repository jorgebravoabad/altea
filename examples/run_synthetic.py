"""End-to-end example on synthetic data, producing figures.

Run from the repository root::

    python examples/run_synthetic.py

Generates a synthetic porous volume, injects acquisition artefacts, runs the
full ALTEA pipeline, and writes QC / morphometry / convergence figures plus a
provenance record to ``runs/example/``. No proprietary data is used.
"""
from pathlib import Path

from altea import Pipeline
from altea.acquire import convergence_study
from altea.datasets import add_acquisition_artifacts, make_porous_volume
from altea.morphometry import porosity
from altea.segment import get_backend
from altea import viz

OUT = Path("runs/example")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    # 1. Synthetic ground-truth volume + realistic corruption.
    clean, ground_truth = make_porous_volume(
        shape=(64, 128, 128), porosity=0.35, seed=0
    )
    raw = add_acquisition_artifacts(
        clean, blur_slices=(8, 40), charge_slices=(20,), drift_px=1.5, seed=1
    )

    # 2. Full pipeline.
    results = Pipeline.from_yaml("configs/fibsem_default.yaml").run(
        raw, output_dir=str(OUT)
    )
    m = results["morphometry"]

    print("=== ALTEA synthetic example ===")
    print("QC summary        :", results["qc_report"].summary())
    print(f"Ground-truth phi  : {ground_truth.mean():.3f}")
    print(f"Measured phi      : {m.porosity:.3f}")
    print(f"Surface area      : {m.specific_surface_area:.4g} 1/{m.units}")
    print(f"Mean pore diameter: {m.psd['mean']:.2f} {m.units}")
    print(f"Tortuosity (z,y,x): {m.tortuosity}")

    # 3. Figures.
    viz.orthoslices(raw, path=OUT / "orthoslices.png")
    viz.qc_panel(results["qc_report"], path=OUT / "qc_panel.png")
    viz.psd_plot(m, path=OUT / "psd.png")

    # 4. Acquisition convergence: how few slices suffice for porosity?
    otsu = get_backend("otsu", invert=True, mode="global")
    conv = convergence_study(
        raw,
        segmenter=otsu.predict,
        descriptor=lambda mask, spacing: porosity(mask),
        descriptor_name="porosity",
    )
    n = conv.slices_for_tolerance(0.02)
    print(f"Slices for 2% porosity error: {n} (of {raw.n_slices})")
    viz.convergence_plot(conv, tol=0.02, path=OUT / "convergence.png")

    print(f"\nFigures and provenance written to: {OUT.resolve()}")


if __name__ == "__main__":
    main()

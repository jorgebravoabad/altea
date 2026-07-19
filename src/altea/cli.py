"""Command-line interface for ALTEA.

Examples
--------
Run the full pipeline on a stack with a config file::

    altea run --input stack.tif --config configs/fibsem_default.yaml --output runs/sample1

Run the built-in synthetic demo (no data required)::

    altea demo --output runs/demo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> int:
    from . import io
    from .pipeline import Pipeline, load_config

    volume = io.load_stack(args.input)
    pipe = Pipeline(load_config(args.config)) if args.config else Pipeline()
    results = pipe.run(volume, output_dir=args.output)
    if "morphometry" in results:
        print(json.dumps(results["morphometry"].to_dict(), indent=2))
    if args.output:
        print(f"\nOutputs and provenance written to: {args.output}", file=sys.stderr)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from .datasets import add_acquisition_artifacts, make_porous_volume
    from .pipeline import Pipeline

    clean, gt = make_porous_volume(porosity=0.35, seed=0)
    raw = add_acquisition_artifacts(
        clean, blur_slices=(8, 30), charge_slices=(15,), seed=1
    )
    results = Pipeline().run(raw, output_dir=args.output)
    report = results["morphometry"]
    print("QC:", results["qc_report"].summary())
    print(f"Ground-truth porosity : {gt.mean():.3f}")
    print(f"Measured porosity     : {report.porosity:.3f}")
    print(f"Specific surface area : {report.specific_surface_area:.4g} 1/{report.units}")
    print(f"Tortuosity (z,y,x)    : {report.tortuosity}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="altea", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run the pipeline on a stack")
    p_run.add_argument("--input", required=True, help="TIFF file or slice directory")
    p_run.add_argument("--config", default=None, help="YAML config file")
    p_run.add_argument("--output", default=None, help="output directory")
    p_run.set_defaults(func=_cmd_run)

    p_demo = sub.add_parser("demo", help="run a synthetic demonstration")
    p_demo.add_argument("--output", default="runs/demo", help="output directory")
    p_demo.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""End-to-end pipeline orchestration.

A :class:`Pipeline` reads a YAML configuration describing which stages to run
and with what parameters, executes them in order on an input volume, and emits
a complete provenance record alongside the outputs. The stage list is explicit
and the configuration is the single source of truth, so a run is fully
described by ``config + input hash`` -- the antithesis of an ad-hoc,
per-sample, adjust-by-eye workflow.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import yaml

from ..core import Volume
from ..provenance import ProvenanceRecord, StageRecord
from .. import align, io, morphometry, preprocess, qc, segment


DEFAULT_CONFIG: Dict[str, Any] = {
    "qc": {"enabled": True, "params": {}},
    "align": {"enabled": True, "upsample_factor": 10},
    "preprocess": {
        "enabled": True,
        "denoise": {"method": "median", "size": 3},
        "normalize": {"method": "percentile"},
    },
    "segment": {"backend": "otsu", "params": {"invert": True, "mode": "global"}},
    "morphometry": {"enabled": True, "compute_tortuosity": True, "psd_bins": 20},
}


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load a YAML config and merge it over the defaults (shallow per section)."""
    user = yaml.safe_load(Path(path).read_text()) or {}
    merged = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    for section, value in user.items():
        if isinstance(value, dict) and isinstance(merged.get(section), dict):
            merged[section].update(value)
        else:
            merged[section] = value
    return merged


class Pipeline:
    """Configurable QC -> align -> preprocess -> segment -> morphometry pipeline."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or json.loads(json.dumps(DEFAULT_CONFIG))
        self.provenance = ProvenanceRecord(config=self.config)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Pipeline":
        return cls(load_config(path))

    # -- stage helpers ---------------------------------------------------
    def _timed(self, name: str, fn, vol_in: Optional[Volume], params: Dict[str, Any]):
        t0 = time.perf_counter()
        result = fn()
        dt = time.perf_counter() - t0
        rec = StageRecord(
            name=name,
            params=params,
            duration_s=round(dt, 4),
            input_hash=vol_in.hash() if vol_in is not None else None,
        )
        return result, rec

    # -- main entry ------------------------------------------------------
    def run(
        self,
        volume: Volume,
        output_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """Execute the configured stages and return a results dict."""
        cfg = self.config
        self.provenance.input_hash = volume.hash()
        results: Dict[str, Any] = {}
        current = volume

        # 1. Quality control -------------------------------------------
        if cfg.get("qc", {}).get("enabled", True):
            params = cfg["qc"].get("params", {})
            report, rec = self._timed(
                "qc", lambda: qc.run_qc(current, **params), current, params
            )
            current = qc.apply_report(current, report)
            rec.metrics = report.summary()
            rec.output_hash = current.hash()
            self.provenance.add_stage(rec)
            results["qc_report"] = report

        # 2. Drift correction ------------------------------------------
        if cfg.get("align", {}).get("enabled", True):
            uf = cfg["align"].get("upsample_factor", 10)
            (aligned_and_shifts, rec) = self._timed(
                "align",
                lambda: align.correct_drift(current, upsample_factor=uf),
                current,
                {"upsample_factor": uf},
            )
            current, shifts = aligned_and_shifts
            rec.metrics = {"max_shift_px": float(np.abs(shifts).max())}
            rec.output_hash = current.hash()
            self.provenance.add_stage(rec)

        # 3. Preprocessing ---------------------------------------------
        if cfg.get("preprocess", {}).get("enabled", True):
            pp = cfg["preprocess"]
            dn = pp.get("denoise", {})
            nm = pp.get("normalize", {})

            def _pre():
                v = current
                if dn:
                    v = preprocess.denoise(v, **dn)
                if nm:
                    v = preprocess.normalize_contrast(v, **nm)
                return v

            current, rec = self._timed("preprocess", _pre, current, pp)
            rec.output_hash = current.hash()
            self.provenance.add_stage(rec)

        # 4. Segmentation ----------------------------------------------
        seg_cfg = cfg.get("segment", {})
        backend_name = seg_cfg.get("backend", "otsu")
        backend_params = seg_cfg.get("params", {})
        backend = segment.get_backend(backend_name, **backend_params)

        labels_ref = seg_cfg.get("labels")  # optional training labels (learned)
        train_labels = None
        if labels_ref:
            train_labels = io.load_stack(labels_ref).data

        def _seg():
            return backend.fit_predict(current, train_labels)

        seg_params = {"backend": backend_name, **backend_params}
        mask, rec = self._timed("segment", _seg, current, seg_params)
        # Interpret the phase of interest.
        phase = seg_cfg.get("phase_label", None)
        if phase is not None:
            binary = mask == phase
        else:
            binary = mask.astype(bool)
        rec.metrics = {"phase_fraction": float(binary.mean())}
        self.provenance.add_stage(rec)
        results["labels"] = mask
        results["mask"] = binary

        # 5. Morphometry -----------------------------------------------
        if cfg.get("morphometry", {}).get("enabled", True):
            mp = cfg["morphometry"]

            def _morph():
                return morphometry.analyze_volume(
                    current,
                    binary,
                    compute_tortuosity=mp.get("compute_tortuosity", True),
                    psd_bins=mp.get("psd_bins", 20),
                )

            report, rec = self._timed("morphometry", _morph, current, mp)
            rec.metrics = {
                "porosity": report.porosity,
                "specific_surface_area": report.specific_surface_area,
            }
            self.provenance.add_stage(rec)
            results["morphometry"] = report

        # -- outputs ----------------------------------------------------
        if output_dir is not None:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            io.save_labels(binary, out / "mask.tif")
            if "morphometry" in results:
                (out / "morphometry.json").write_text(
                    json.dumps(results["morphometry"].to_dict(), indent=2)
                )
            self.provenance.save(out / "provenance.json")
            results["output_dir"] = str(out)

        results["provenance"] = self.provenance
        return results

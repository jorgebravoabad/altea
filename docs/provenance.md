# Provenance

Every `Pipeline` run emits a machine-readable record of exactly what was done.
This is the core of ALTEA's reproducibility claim: a run is fully described by
its configuration plus the hash of its input, and that description is written to
disk rather than asserted.

## What gets recorded

```json
{
  "altea_version": "0.1.0",
  "created_utc": "2026-07-19T14:22:31+00:00",
  "python_version": "3.12.3",
  "platform": "Linux-6.8.0-x86_64",
  "dependency_versions": {
    "numpy": "2.1.0", "scipy": "1.14.0", "scikit-image": "0.26.0", "...": "..."
  },
  "git_commit": "a1b2c3d...",
  "input_hash": "43d1cfadd38b25f7...",
  "config": { "...resolved configuration, defaults included..." },
  "stages": [
    {
      "name": "qc",
      "params": {"sharpness_z": -2.5, "brightness_z": 3.0},
      "metrics": {"n_slices": 400, "n_kept": 383, "n_dropped": 17,
                  "drop_reasons": {"drift": 9, "charging": 5, "blur": 3}},
      "input_hash": "43d1cfad...", "output_hash": "9f2ab71c...",
      "duration_s": 0.0238
    }
  ]
}
```

## Using it

```python
results = Pipeline.from_yaml("config.yaml").run(volume, output_dir="runs/s1")
prov = results["provenance"]

prov.save("runs/s1/provenance.json")

for stage in prov.stages:
    print(f"{stage.name:12s} {stage.duration_s:7.3f}s  {stage.metrics}")
```

Reload a record later:

```python
from altea import ProvenanceRecord

prov = ProvenanceRecord.load("runs/s1/provenance.json")
print(prov.config["segment"]["backend"])
```

## Why the input hash matters

The hash is computed over the array contents, not the filename. Two runs with
the same `input_hash` and the same `config` should produce identical results —
and if they don't, something in the environment changed, which the recorded
dependency versions will help you locate.

```python
volume.hash()   # deterministic content hash
```

## Reproducibility checklist

For results you intend to publish:

1. Run through `Pipeline`, not hand-composed stages, so the record is complete.
2. Keep the `provenance.json` alongside the figures it produced.
3. Version the config file with your analysis code.
4. Record the ALTEA version — `pip install altea==0.1.0` pins it exactly.
5. Cite the archived release DOI (see {doc}`citing`).

```{admonition} What provenance does not cover
:class: caution

The record captures the *analysis*. It does not capture acquisition parameters
(beam settings, dwell time, milling step) — those live in your instrument's
metadata and should be archived alongside. ALTEA stores whatever you put in
`Volume.metadata`, so attaching them there is a good habit.
```

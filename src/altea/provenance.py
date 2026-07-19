"""Provenance tracking: the reproducibility backbone of ALTEA.

Every pipeline run emits a :class:`ProvenanceRecord` capturing exactly what was
done: the resolved configuration, the software and dependency versions, a hash
of the input data, the per-stage parameters and the resulting metrics. Written
next to the outputs as JSON, this record is what turns an ad-hoc, "adjust the
filters by eye" workflow into a versioned, auditable and repeatable procedure.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

_TRACKED_PACKAGES = (
    "numpy",
    "scipy",
    "scikit-image",
    "scikit-learn",
    "tifffile",
    "pyyaml",
    "matplotlib",
)


def _package_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:  # pragma: no cover
            versions[name] = "not-installed"
    return versions


def _git_commit() -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode().strip()
    except Exception:  # pragma: no cover - git may be absent
        return None


def _altea_version() -> str:
    try:
        return importlib_metadata.version("altea")
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "0.1.0+source"


@dataclass
class StageRecord:
    """Provenance for a single pipeline stage."""

    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    duration_s: Optional[float] = None


@dataclass
class ProvenanceRecord:
    """Complete, serializable description of a pipeline run."""

    altea_version: str = field(default_factory=_altea_version)
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)
    dependency_versions: Dict[str, str] = field(default_factory=_package_versions)
    git_commit: Optional[str] = field(default_factory=_git_commit)
    config: Dict[str, Any] = field(default_factory=dict)
    input_hash: Optional[str] = None
    stages: List[StageRecord] = field(default_factory=list)

    def add_stage(self, stage: StageRecord) -> None:
        self.stages.append(stage)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ProvenanceRecord":
        raw = json.loads(Path(path).read_text())
        stages = [StageRecord(**s) for s in raw.pop("stages", [])]
        rec = cls(**raw)
        rec.stages = stages
        return rec

"""Contract between the runner and the problem modules.

Created 2026-09-06 to collect diverse CP-SAT logs as base data for the log
analyzer. Each module in ``bench/problems/`` exposes a ``PROBLEM: Problem``:

    PROBLEM = Problem(
        name="jobshop",
        description="Classic job-shop scheduling from JSPLIB",
        download=download,      # (data_dir: Path) -> None; idempotent, fetches instance files
        instances=instances,    # (data_dir: Path) -> list[Instance]; sorted by expected difficulty
        build=build,            # (instance: Instance) -> cp_model.CpModel (with objective if any)
    )

Keep modules self-contained (parsing + model) and avoid heavy dependencies:
only ``ortools`` and the standard library are available.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Instance:
    name: str  # file-system safe, unique within the problem
    path: Path | None = None  # instance file, None for generated instances
    meta: dict[str, Any] = field(default_factory=dict)  # size hints for the metadata file


@dataclass(frozen=True)
class Problem:
    name: str
    description: str
    download: Callable[[Path], None]
    instances: Callable[[Path], list[Instance]]
    build: Callable[[Instance], cp_model.CpModel]
    source: str = ""  # URL of the instance collection


def fetch(url: str, dest: Path, timeout: float = 120.0) -> Path:
    """Download ``url`` to ``dest`` unless it already exists; returns ``dest``."""
    import urllib.request

    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "cpsat-log-benchmarks/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    return dest

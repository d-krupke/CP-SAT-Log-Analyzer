"""Solve instances with CP-SAT and store the full search log plus metadata.

Created 2026-09-06. Logs land in ``logs/<problem>/<instance>__w<workers>_t<limit>.txt``
with a sibling ``.json`` (problem, instance, parameters, status, objective, bound,
wall time, model size). Existing logs are skipped so runs can be resumed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from .base import Instance, Problem


def log_path(
    logs_dir: Path, problem: str, instance: str, workers: int, limit: float, tag: str = ""
) -> Path:
    suffix = f"_{tag}" if tag else ""
    return logs_dir / problem / f"{instance}__w{workers}_t{int(limit)}{suffix}.txt"


def solve_and_log(
    problem: Problem,
    instance: Instance,
    logs_dir: Path,
    *,
    time_limit: float,
    workers: int,
    extra_params: dict[str, Any] | None = None,
    tag: str = "",
    force: bool = False,
) -> dict[str, Any] | None:
    """Build, solve and log one instance; returns the metadata (None if skipped)."""
    out = log_path(logs_dir, problem.name, instance.name, workers, time_limit, tag)
    if out.exists() and not force:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    model = problem.build(instance)
    build_s = time.time() - t0

    solver = cp_model.CpSolver()
    p = solver.parameters
    p.max_time_in_seconds = time_limit
    p.num_workers = workers
    p.log_search_progress = True
    p.log_to_stdout = False
    p.log_subsolver_statistics = True
    for key, value in (extra_params or {}).items():
        setattr(p, key, value)
    lines: list[str] = []
    solver.log_callback = lines.append
    status = solver.solve(model)

    meta = {
        "problem": problem.name,
        "instance": instance.name,
        "instance_meta": instance.meta,
        "source": problem.source,
        "parameters": {"max_time_in_seconds": time_limit, "num_workers": workers, **(extra_params or {})},
        "ortools_version": _ortools_version(),
        "status": solver.status_name(status),
        "objective": solver.objective_value if _has_objective(model) else None,
        "best_bound": solver.best_objective_bound if _has_objective(model) else None,
        "wall_time": solver.wall_time,
        "build_seconds": round(build_s, 3),
        "num_variables": len(model.proto.variables),
        "num_constraints": len(model.proto.constraints),
        "log_lines": len(lines),
    }
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return meta


def _has_objective(model: cp_model.CpModel) -> bool:
    proto = model.proto
    if hasattr(proto, "has_objective"):  # pybind proto of ortools >= 9.15
        return bool(proto.has_objective() or proto.has_floating_point_objective())
    return proto.HasField("objective") or proto.HasField("floating_point_objective")


def _ortools_version() -> str:
    try:
        import ortools

        return ortools.__version__
    except Exception:  # noqa: BLE001
        return "unknown"

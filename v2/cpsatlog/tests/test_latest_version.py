"""Smoke test against the OR-Tools version installed in the dev environment.

Generates a small knapsack log with the installed ``ortools`` and checks that the
parser recognizes the version, the response and at least one solution event.
This catches format changes as soon as a new OR-Tools release is installed.
"""

from __future__ import annotations

import pytest

from cpsatlog import parse_log

ortools = pytest.importorskip("ortools")


def _generate_log() -> str:
    import random

    from ortools.sat.python import cp_model

    rng = random.Random(1)
    model = cp_model.CpModel()
    n = 300
    xs = [model.new_bool_var(f"x{i}") for i in range(n)]
    weights = [rng.randint(1, 100) for _ in range(n)]
    values = [rng.randint(1, 100) for _ in range(n)]
    model.add(sum(w * x for w, x in zip(weights, xs, strict=True)) <= sum(weights) // 3)
    model.maximize(sum(v * x for v, x in zip(values, xs, strict=True)))
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.log_to_stdout = False
    solver.parameters.max_time_in_seconds = 3
    solver.parameters.num_workers = 4
    lines: list[str] = []
    solver.log_callback = lines.append
    solver.solve(model)
    return "\n".join(lines)


def test_installed_ortools_log_parses() -> None:
    log = parse_log(_generate_log())
    assert log.solver is not None and log.solver.version is not None
    assert log.solver.version.value == ortools.__version__
    assert log.response is not None and log.response.status is not None
    assert log.response.status.value in {"OPTIMAL", "FEASIBLE"}
    assert log.search is not None and log.search.objective_sense == "maximize"
    assert log.search.events_of_kind("solution")
    assert log.stats.search_stats is not None
    assert log.unparsed == [], [b.lines[0].value for b in log.unparsed]

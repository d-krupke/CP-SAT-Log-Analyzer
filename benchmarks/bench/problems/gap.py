"""Generalized assignment problem (GAP) from Beasley's OR-Library.

What: one problem class of the CP-SAT log benchmark harness.  Created
2026-09-06 as a mid-difficulty 0/1 model that mixes two constraint kinds an
analyzer should recognize: an exactly-one block per job (assignment structure)
and one knapsack per agent.  Small instances close in milliseconds, the large
``gapc``/``gapd`` ones leave a stubborn gap, so one problem class yields both
"solved in presolve" and "gap never closes" logs.

Source: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/gapinfo.html
Files:  https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/gap1.txt etc.

Format (whitespace separated, line wrapping is irrelevant)::

    P                       number of instances in the file
    for each instance:
        m n                 agents, jobs
        c_11 ... c_1n       cost/profit matrix, m rows of n entries
        ...
        a_11 ... a_1n       resource matrix, m rows of n entries
        ...
        b_1 ... b_m         capacity per agent

Important: ``gap1``-``gap12`` are **maximization** instances (Martello & Toth
style, optimum of the first ``gap1`` instance is 336), whereas ``gapa``-``gapd``
are **minimization** instances.  This module keeps the file's own sense instead
of negating, so the logs contain both directions.

Model: Boolean ``x[i][j]``, one ``AddExactlyOne`` per job over the agents, one
linear ``<=`` per agent, and the objective in the file's own direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files"

MAXIMIZATION_FILES = frozenset(f"gap{i}" for i in range(1, 13))
FILES: tuple[str, ...] = (
    *(f"gap{i}" for i in range(1, 13)),
    "gapa",
    "gapb",
    "gapc",
    "gapd",
)

# (file, index inside the file), ordered easy -> hard.  gap1..gap12 grow from
# 5x15 to 10x60; gapa..gapd hold the six shapes 5/10/20 agents x 100/200 jobs,
# with gapb..gapd only contributing the two 200-job shapes each.
SELECTION: tuple[tuple[str, int], ...] = (
    *((f"gap{i}", 0) for i in range(1, 13)),
    ("gapa", 0),
    ("gapa", 2),
    ("gapa", 4),
    ("gapa", 1),
    ("gapa", 3),
    ("gapa", 5),
    ("gapb", 3),
    ("gapb", 5),
    ("gapc", 3),
    ("gapc", 5),
    ("gapd", 3),
    ("gapd", 5),
)


@dataclass(frozen=True)
class GapData:
    """One parsed GAP instance; ``maximize`` comes from the file family."""

    num_agents: int
    num_jobs: int
    cost: list[list[int]]
    resource: list[list[int]]
    capacity: list[int]
    maximize: bool


def parse_gap(path: Path, *, maximize: bool) -> list[GapData]:
    """Parse all instances of one OR-Library ``gap`` file."""
    tokens = path.read_text().split()
    pos = 0

    def take(count: int) -> list[int]:
        nonlocal pos
        chunk = [int(float(t)) for t in tokens[pos : pos + count]]
        pos += count
        return chunk

    num_problems = take(1)[0]
    out: list[GapData] = []
    for _ in range(num_problems):
        m, n = take(2)
        cost = [take(n) for _ in range(m)]
        resource = [take(n) for _ in range(m)]
        capacity = take(m)
        out.append(GapData(m, n, cost, resource, capacity, maximize))
    if pos != len(tokens):
        raise ValueError(f"{path.name}: {len(tokens) - pos} trailing tokens")
    return out


def download(data_dir: Path) -> None:
    for name in FILES:
        fetch(f"{BASE_URL}/{name}.txt", data_dir / f"{name}.txt")


def instances(data_dir: Path) -> list[Instance]:
    cache: dict[str, list[GapData]] = {}
    out: list[Instance] = []
    for file_name, index in SELECTION:
        path = data_dir / f"{file_name}.txt"
        if not path.exists():
            continue
        if file_name not in cache:
            cache[file_name] = parse_gap(path, maximize=file_name in MAXIMIZATION_FILES)
        problems = cache[file_name]
        if index >= len(problems):
            continue
        data = problems[index]
        out.append(
            Instance(
                name=f"{file_name}_{index:02d}",
                path=path,
                meta={
                    "index_in_file": index,
                    "agents": data.num_agents,
                    "jobs": data.num_jobs,
                    "sense": "maximize" if data.maximize else "minimize",
                },
            )
        )
    return out


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    file_name = instance.name.rsplit("_", 1)[0]
    index = int(instance.meta["index_in_file"])
    data = parse_gap(instance.path, maximize=file_name in MAXIMIZATION_FILES)[index]

    m, n = data.num_agents, data.num_jobs
    model = cp_model.CpModel()
    x = [[model.new_bool_var(f"x_{i}_{j}") for j in range(n)] for i in range(m)]
    for j in range(n):
        model.add_exactly_one(x[i][j] for i in range(m))
    for i in range(m):
        model.add(
            cp_model.LinearExpr.weighted_sum(x[i], data.resource[i]) <= data.capacity[i]
        )
    objective = cp_model.LinearExpr.sum(
        [cp_model.LinearExpr.weighted_sum(x[i], data.cost[i]) for i in range(m)]
    )
    if data.maximize:
        model.maximize(objective)
    else:
        model.minimize(objective)
    return model


PROBLEM = Problem(
    name="gap",
    description="Generalized assignment (OR-Library gap1-12 max, gapa-d min)",
    download=download,
    instances=instances,
    build=build,
    source="https://people.brunel.ac.uk/~mastjjb/jeb/orlib/gapinfo.html",
)

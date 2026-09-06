"""Minimum dominating set on the DIMACS COLOR benchmark graphs.

Created 2026-09-06 for the CP-SAT log benchmarks. Dominating set is a pure
set-cover-style Boolean model: no symmetry to break, a decent LP relaxation and
a small variable count, so its logs are dominated by the LP/cut loop and by
presolve reductions -- a deliberate contrast to the colouring and clique models
that use the same graphs.

Instances: the classic DIMACS colouring set, ASCII ``.col`` files from
https://mat.tepper.cmu.edu/COLOR02/INSTANCES/ (format: see
``bench/problems/_dimacs.py``). This module keeps its own copies under
``data/dominating_set/`` so it stays independent of ``graph_coloring``.

Model: one Boolean ``x[v]`` "v is in the dominating set", one ``add_bool_or``
over the closed neighbourhood ``N(v) + v`` per vertex, and ``minimize sum(x)``.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch
from . import _dimacs

_CMU = "https://mat.tepper.cmu.edu/COLOR02/INSTANCES"

# Roughly easy -> hard. Sparse graphs are the hard ones here: a dense graph is
# dominated by very few vertices, while the sparse le450/DSJC/school instances
# leave a large, weakly constrained cover problem.
_ORDER: tuple[str, ...] = (
    "myciel3",
    "queen5_5",
    "myciel4",
    "queen6_6",
    "myciel5",
    "queen7_7",
    "jean",
    "huck",
    "queen8_8",
    "david",
    "anna",
    "games120",
    "queen9_9",
    "myciel6",
    "miles250",
    "queen8_12",
    "myciel7",
    "DSJC125.1",
    "le450_5a",
    "school1",
)


def download(data_dir: Path) -> None:
    """Fetch every ``.col`` file (~0.3 MB in total); idempotent via ``fetch``."""
    for name in _ORDER:
        fetch(f"{_CMU}/{name}.col", data_dir / f"{name}.col")


def instances(data_dir: Path) -> list[Instance]:
    found: list[Instance] = []
    for name in _ORDER:
        path = data_dir / f"{name}.col"
        if not path.exists():
            continue
        graph = _dimacs.parse_graph(path)
        degrees = [len(nb) for nb in graph.neighbours()]
        found.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "vertices": graph.num_vertices,
                    "edges": graph.num_edges,
                    "density": round(graph.density, 4),
                    "min_degree": min(degrees, default=0),
                },
            )
        )
    return found


def build(instance: Instance) -> cp_model.CpModel:
    """Set-cover model: every closed neighbourhood must contain a chosen vertex."""
    assert instance.path is not None
    graph = _dimacs.parse_graph(instance.path)
    adjacency = graph.neighbours()

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x[{v}]") for v in range(graph.num_vertices)]
    for v in range(graph.num_vertices):
        model.add_bool_or([x[v], *(x[u] for u in sorted(adjacency[v]))])
    model.minimize(sum(x))
    return model


PROBLEM = Problem(
    name="dominating_set",
    description="Minimum dominating set on the DIMACS COLOR02 benchmark graphs",
    download=download,
    instances=instances,
    build=build,
    source="https://mat.tepper.cmu.edu/COLOR02/",
)

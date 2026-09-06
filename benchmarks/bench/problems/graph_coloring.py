"""Minimum graph colouring on the DIMACS COLOR benchmark graphs.

Created 2026-09-06 for the CP-SAT log benchmarks: colouring gives logs with a
strong LP/clique lower bound, heavy symmetry and a long objective staircase,
which is exactly the kind of search progress the log analyzer must explain.

Instances: the classic DIMACS colouring set, ASCII ``.col`` (see
``bench/problems/_dimacs.py`` for the format).
  * https://mat.tepper.cmu.edu/COLOR02/INSTANCES/ (COLOR02/03/04, most files)
  * https://cedric.cnam.fr/~porumbed/graphs/ (mirror for the three files that
    CMU only ships in the binary ``.col.b`` format: flat300_28_0, r125.1, r125.5)

Model: one Boolean ``x[v,c]`` per vertex/colour with ``add_exactly_one`` per
vertex, ``add_at_most_one`` per (clique of an edge clique cover, colour) instead
of a clause per (edge, colour), ``y[c]`` "colour c is used" Booleans with
``x[v,c] => y[c]`` and the symmetry break ``y[c] >= y[c+1]``, the colours of a
greedy maximal clique fixed to ``0..k-1``, and ``minimize sum(y)``. The number of
available colours is the DSATUR upper bound, so the model is always feasible.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch
from . import _dimacs

_CMU = "https://mat.tepper.cmu.edu/COLOR02/INSTANCES"
_CNAM = "https://cedric.cnam.fr/~porumbed/graphs"
# CMU only has these three as binary .col.b, so take the ASCII mirror.
_MIRROR = {"flat300_28_0": _CNAM, "r125.1": _CNAM, "r125.5": _CNAM}

# Roughly easy -> hard (small/sparse first, then the dense random and the
# structured quasigroup instances). latin_square_10 is deliberately absent: its
# assignment model needs ~5.4M constraints (900 vertices, 307k edges, DSATUR
# bound 132), which is far beyond a sane build time.
_ORDER: tuple[str, ...] = (
    "myciel3",
    "myciel4",
    "queen5_5",
    "queen6_6",
    "huck",
    "jean",
    "david",
    "anna",
    "myciel5",
    "queen7_7",
    "r125.1",
    "games120",
    "miles250",
    "queen8_8",
    "myciel6",
    "queen9_9",
    "miles500",
    "mulsol.i.1",
    "zeroin.i.1",
    "r125.5",
    "DSJC125.1",
    "myciel7",
    "miles750",
    "queen8_12",
    "miles1000",
    "fpsol2.i.1",
    "inithx.i.1",
    "le450_5a",
    "DSJC125.5",
    "le450_15a",
    "DSJC125.9",
    "le450_25a",
    "school1",
    "DSJC250.5",
    "flat300_28_0",
    "qg.order30",
)


def _url(name: str) -> str:
    return f"{_MIRROR.get(name, _CMU)}/{name}.col"


def download(data_dir: Path) -> None:
    """Fetch every ``.col`` file (~1.5 MB in total); idempotent via ``fetch``."""
    for name in _ORDER:
        fetch(_url(name), data_dir / f"{name}.col")


def instances(data_dir: Path) -> list[Instance]:
    found: list[Instance] = []
    for name in _ORDER:
        path = data_dir / f"{name}.col"
        if not path.exists():
            continue
        graph = _dimacs.parse_graph(path)
        found.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "vertices": graph.num_vertices,
                    "edges": graph.num_edges,
                    "density": round(graph.density, 4),
                },
            )
        )
    return found


def build(instance: Instance) -> cp_model.CpModel:
    """Assignment model for the minimum number of colours."""
    assert instance.path is not None
    graph = _dimacs.parse_graph(instance.path)
    num_vertices = graph.num_vertices
    max_colors = max(1, _dimacs.dsatur_num_colors(graph))
    clique = _dimacs.greedy_clique(graph)[:max_colors]

    model = cp_model.CpModel()
    x = [[model.new_bool_var(f"x[{v},{c}]") for c in range(max_colors)] for v in range(num_vertices)]
    used = [model.new_bool_var(f"used[{c}]") for c in range(max_colors)]

    for v in range(num_vertices):
        model.add_exactly_one(x[v])

    # One AtMostOne per (clique, colour): a clique of size s subsumes s*(s-1)/2
    # edge clauses, which keeps dense instances buildable and propagates better.
    for group in _dimacs.edge_clique_cover(graph):
        for c in range(max_colors):
            model.add_at_most_one(x[v][c] for v in group)

    for v in range(num_vertices):
        for c in range(max_colors):
            model.add_implication(x[v][c], used[c])
    # Symmetry breaking: colours are interchangeable, so use them in order.
    for c in range(max_colors - 1):
        model.add(used[c] >= used[c + 1])
    # A maximal clique needs |clique| distinct colours; fix them to 0..k-1.
    for index, vertex in enumerate(clique):
        model.add(x[vertex][index] == 1)

    model.minimize(sum(used))
    return model


PROBLEM = Problem(
    name="graph_coloring",
    description="Minimum graph colouring on the DIMACS COLOR02 benchmark graphs",
    download=download,
    instances=instances,
    build=build,
    source="https://mat.tepper.cmu.edu/COLOR02/",
)

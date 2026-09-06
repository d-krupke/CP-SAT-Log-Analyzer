"""Traveling salesman instances from TSPLIB95, modeled with ``add_circuit``.

Created 2026-09-06 for the CP-SAT log benchmark harness: TSP is the canonical
``add_circuit`` workload, so its logs show what routing-style search looks like
(strong LP bounds, many "reduced cost fixing" / routing cut lines).

Instances: TSPLIB95 by G. Reinelt,
http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/ -- the original
Heidelberg host is frequently unreachable, so the files are pulled from
GitHub mirrors (symmetric ``.tsp`` from ``mastqe/tsplib``, asymmetric ``.atsp``
from ``coin-or/jorlib``). Format and distance rules: see ``_tsplib.py``.

35 symmetric instances (14..318 nodes, EUC_2D / GEO / ATT / EXPLICIT) plus 7
asymmetric ones (34..100 nodes, FULL_MATRIX), sorted by node count. Objective
values are directly comparable with the published TSPLIB optima.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch
from . import _tsplib

TSP_BASE = "https://raw.githubusercontent.com/mastqe/tsplib/master"
ATSP_BASE = "https://raw.githubusercontent.com/coin-or/jorlib/master/jorlib-core/src/test/resources/tspLib/atsp"

#: Symmetric instances, roughly ordered by size; mixes all supported weight types.
SYMMETRIC = [
    "burma14",
    "ulysses16",
    "gr17",
    "gr21",
    "gr24",
    "fri26",
    "bayg29",
    "bays29",
    "dantzig42",
    "att48",
    "gr48",
    "hk48",
    "eil51",
    "berlin52",
    "brazil58",
    "st70",
    "eil76",
    "pr76",
    "gr96",
    "rat99",
    "kroA100",
    "lin105",
    "pr107",
    "gr120",
    "bier127",
    "pr144",
    "ch150",
    "si175",
    "brg180",
    "rat195",
    "d198",
    "kroA200",
    "gil262",
    "a280",
    "lin318",
]

#: Asymmetric instances (EXPLICIT FULL_MATRIX); exercise the same model without
#: the symmetry that CP-SAT's routing propagators like.
ASYMMETRIC = ["ftv33", "ftv44", "ry48p", "ft53", "ftv55", "ft70", "kro124p"]


def download(data_dir: Path) -> None:
    """Fetch every selected instance file (idempotent, ~2 MB in total)."""
    for name in SYMMETRIC:
        fetch(f"{TSP_BASE}/{name}.tsp", data_dir / f"{name}.tsp")
    for name in ASYMMETRIC:
        fetch(f"{ATSP_BASE}/{name}.atsp", data_dir / f"{name}.atsp")


def instances(data_dir: Path) -> list[Instance]:
    """All downloaded instances, easy first (by node count, then name)."""
    found: list[tuple[int, str, Path]] = []
    for path in sorted(data_dir.glob("*.tsp")) + sorted(data_dir.glob("*.atsp")):
        try:
            nodes = _tsplib.read_dimension(path)
        except (OSError, ValueError):
            continue
        found.append((nodes, path.stem, path))
    out: list[Instance] = []
    for nodes, name, path in sorted(found):
        out.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "nodes": nodes,
                    "arcs": nodes * (nodes - 1),
                    "symmetric": path.suffix == ".tsp",
                },
            )
        )
    return out


def build(instance: Instance) -> cp_model.CpModel:
    """One Boolean per ordered pair, ``add_circuit`` over them, minimize length.

    ``add_circuit`` needs a directed arc set, so both orientations get their own
    literal even for symmetric instances; the circuit constraint already rules
    out using both of them (every node has in-degree and out-degree one).
    """
    assert instance.path is not None
    parsed = _tsplib.parse(instance.path)
    dist = _tsplib.distance_matrix(parsed)
    n = parsed.dimension

    model = cp_model.CpModel()
    model.name = f"tsp_{parsed.name}_n{n}"
    arcs: list[tuple[int, int, cp_model.LiteralT]] = []
    literals: list[cp_model.IntVar] = []
    weights: list[int] = []
    for i in range(n):
        row = dist[i]
        for j in range(n):
            if i == j:
                continue
            lit = model.new_bool_var(f"x[{i},{j}]")
            arcs.append((i, j, lit))
            literals.append(lit)
            weights.append(int(row[j]))
    model.add_circuit(arcs)
    model.minimize(cp_model.LinearExpr.weighted_sum(literals, weights))
    return model


PROBLEM = Problem(
    name="tsp",
    description="Symmetric/asymmetric TSP from TSPLIB95 via add_circuit (14-318 nodes)",
    download=download,
    instances=instances,
    build=build,
    source="http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/",
)

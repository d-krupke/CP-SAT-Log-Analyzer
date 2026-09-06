"""Capacitated vehicle routing (CVRPLIB) modeled with ``add_multiple_circuit``.

Created 2026-09-06 for the CP-SAT log benchmark harness. CVRP complements the
pure ``tsp`` module: same arc-literal graph, but a multi-route circuit plus a
side constraint (capacity), which produces markedly different logs -- weaker
bounds, long plateaus, lots of LNS activity.

Instances: CVRPLIB, https://galgos.inf.puc-rio.br/cvrplib/ (formerly
http://vrp.atd-lab.inf.puc-rio.br/) -- classic Augerat sets A, B and P. The
CVRPLIB site only serves files behind opaque numeric ids nowadays, so the files
are pulled from the GitHub mirror ``afurculita/VehicleRoutingProblem``
(``datasets/small``), which carries the unmodified TSPLIB-style ``.vrp`` files.

Format: TSPLIB95 with ``EDGE_WEIGHT_TYPE : EUC_2D``, ``CAPACITY``,
``DEMAND_SECTION`` and ``DEPOT_SECTION`` (see ``_tsplib.py``). 26 instances
with 16..80 nodes, sorted by node count.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch
from . import _tsplib

BASE = "https://raw.githubusercontent.com/afurculita/VehicleRoutingProblem/master/datasets/small"

#: Augerat A/B/P instances, easy -> hard. ``k`` in the name is the fleet size of
#: the best known solution and is used as the vehicle-count upper bound.
NAMES = [
    "P-n16-k8",
    "P-n19-k2",
    "P-n20-k2",
    "P-n22-k2",
    "P-n23-k8",
    "B-n31-k5",
    "A-n32-k5",
    "A-n33-k5",
    "A-n33-k6",
    "A-n34-k5",
    "B-n34-k5",
    "A-n36-k5",
    "A-n37-k5",
    "A-n39-k5",
    "P-n40-k5",
    "B-n41-k6",
    "A-n45-k6",
    "A-n46-k7",
    "P-n50-k7",
    "B-n50-k7",
    "A-n53-k7",
    "P-n55-k10",
    "A-n60-k9",
    "A-n65-k9",
    "P-n76-k5",
    "A-n80-k10",
]

_K_IN_NAME = re.compile(r"-k(\d+)")


def download(data_dir: Path) -> None:
    """Fetch every selected ``.vrp`` file (idempotent, well under 1 MB)."""
    for name in NAMES:
        fetch(f"{BASE}/{name}.vrp", data_dir / f"{name}.vrp")


def instances(data_dir: Path) -> list[Instance]:
    """All downloaded instances, easy first (node count, then fleet size)."""
    found: list[tuple[int, int, str, Path]] = []
    for path in sorted(data_dir.glob("*.vrp")):
        try:
            nodes = _tsplib.read_dimension(path)
        except (OSError, ValueError):
            continue
        match = _K_IN_NAME.search(path.stem)
        found.append((nodes, int(match.group(1)) if match else 0, path.stem, path))
    out: list[Instance] = []
    for nodes, vehicles, name, path in sorted(found):
        out.append(
            Instance(
                name=name,
                path=path,
                meta={"nodes": nodes, "customers": nodes - 1, "vehicles": vehicles},
            )
        )
    return out


def _vehicle_bounds(instance: Instance, demands: list[int], capacity: int, customers: int) -> tuple[int, int]:
    """Fleet-size window: bin-packing lower bound .. ``k`` from the file name."""
    lower = max(1, math.ceil(sum(demands) / capacity))
    named = int(instance.meta.get("vehicles") or 0)
    upper = max(lower, named) if named else max(lower, customers)
    return lower, min(upper, customers)


def build(instance: Instance) -> cp_model.CpModel:
    """Arc literals + ``add_multiple_circuit`` + cumulative-load capacity.

    Node 0 is the depot; ``add_multiple_circuit`` lets an arbitrary number of
    routes leave and return to it while forbidding any cycle that avoids it. No
    self-loops are added, so every customer must be served. Capacity is enforced
    by a load variable per customer (``demand[i] <= load[i] <= capacity``) tied
    together along each route: arc ``i -> j`` forces
    ``load[j] == load[i] + demand[j]`` (``load[j] == demand[j]`` when it leaves
    the depot). That is the MTZ-style cumulative formulation, which also breaks
    the sub-route symmetry. The objective is the total traveled distance.
    """
    assert instance.path is not None
    parsed = _tsplib.parse(instance.path)
    dist = _tsplib.distance_matrix(parsed)
    n = parsed.dimension
    capacity = parsed.capacity or 0
    if capacity <= 0:
        raise ValueError(f"{instance.name}: missing CAPACITY")
    demands = list(parsed.demands) or [0] * n
    # Normalize so that node 0 is the depot (all Augerat files already are).
    order = [parsed.depot] + [i for i in range(n) if i != parsed.depot]
    if order != list(range(n)):
        dist = [[dist[a][b] for b in order] for a in order]
        demands = [demands[a] for a in order]
    demands[0] = 0
    customers = n - 1
    max_demand = max(demands) if demands else 0
    if max_demand > capacity:
        raise ValueError(f"{instance.name}: demand {max_demand} exceeds capacity {capacity}")

    model = cp_model.CpModel()
    model.name = f"cvrp_{parsed.name}_n{n}_q{capacity}"

    arcs: list[tuple[int, int, cp_model.LiteralT]] = []
    literals: list[cp_model.IntVar] = []
    weights: list[int] = []
    arc_lit: dict[tuple[int, int], cp_model.IntVar] = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            lit = model.new_bool_var(f"x[{i},{j}]")
            arc_lit[(i, j)] = lit
            arcs.append((i, j, lit))
            literals.append(lit)
            weights.append(int(dist[i][j]))
    model.add_multiple_circuit(arcs)

    # Cumulative load along each route; load[0] is unused (depot).
    load = [model.new_int_var(0, 0, "load[0]")] + [
        model.new_int_var(demands[j], capacity, f"load[{j}]") for j in range(1, n)
    ]
    for (i, j), lit in arc_lit.items():
        if j == 0:
            continue
        if i == 0:
            model.add(load[j] == demands[j]).only_enforce_if(lit)
        else:
            model.add(load[j] == load[i] + demands[j]).only_enforce_if(lit)

    lower, upper = _vehicle_bounds(instance, demands, capacity, customers)
    depot_out = [arc_lit[(0, j)] for j in range(1, n)]
    depot_in = [arc_lit[(j, 0)] for j in range(1, n)]
    used = model.new_int_var(lower, upper, "vehicles")
    model.add(sum(depot_out) == used)
    model.add(sum(depot_in) == used)

    model.minimize(cp_model.LinearExpr.weighted_sum(literals, weights))
    return model


PROBLEM = Problem(
    name="cvrp",
    description="Capacitated VRP (Augerat A/B/P) via add_multiple_circuit (16-80 nodes)",
    download=download,
    instances=instances,
    build=build,
    source="https://galgos.inf.puc-rio.br/cvrplib/",
)

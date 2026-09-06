"""Maximum clique on the second DIMACS Implementation Challenge graphs.

Created 2026-09-06 for the CP-SAT log benchmarks: max-clique is a tiny model
(one Boolean per vertex) with a notoriously weak linear relaxation, so its logs
show long plateaus, aggressive clique cuts and a slowly moving dual bound -- a
useful contrast to the big structured models in this suite.

Instances: the classic DIMACS clique benchmark in ASCII ``.clq`` format (see
``bench/problems/_dimacs.py``), taken from the GitHub mirror
https://github.com/jamestrimble/max-weight-clique-instances (``DIMACS/weighted``).
Those files are the original unweighted DIMACS graphs with an extra ``n <v> <w>``
weight line per vertex added by the mirror; the parser ignores ``n`` lines, so
what we solve is the standard *unweighted* maximum clique problem.

Model: one Boolean ``x[v]``, ``maximize sum(x)``, and for every *non*-edge the
requirement that not both endpoints are chosen. The non-edges are grouped into
cliques of the complement graph (= independent sets of the graph) and posted as
``add_at_most_one``, which is both far more compact and much stronger than one
binary clause per non-edge.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch
from . import _dimacs

_BASE = "https://raw.githubusercontent.com/jamestrimble/max-weight-clique-instances/master/DIMACS/weighted"

# Roughly easy -> hard for CP-SAT (the brock/san/gen families are the classic
# adversarial ones; keller5 and DSJC500_5 are open-ended within a minute).
_ORDER: tuple[str, ...] = (
    "MANN_a9",
    "hamming6-2",
    "johnson8-4-4",
    "johnson16-2-4",
    "hamming8-4",
    "keller4",
    "C125.9",
    "p_hat300-1",
    "hamming10-2",
    "brock200_2",
    "brock200_3",
    "brock200_4",
    "sanr200_0.7",
    "brock200_1",
    "san200_0.7_1",
    "p_hat500-1",
    "p_hat300-2",
    "san200_0.9_1",
    "gen200_p0.9_44",
    "MANN_a27",
    "C250.9",
    "p_hat300-3",
    "brock400_1",
    "DSJC500_5",
    "keller5",
)


def download(data_dir: Path) -> None:
    """Fetch every ``.clq`` file (~12 MB in total); idempotent via ``fetch``."""
    for name in _ORDER:
        fetch(f"{_BASE}/{name}.clq", data_dir / f"{name}.clq")


def instances(data_dir: Path) -> list[Instance]:
    found: list[Instance] = []
    for name in _ORDER:
        path = data_dir / f"{name}.clq"
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
                    "non_edges": graph.num_vertices * (graph.num_vertices - 1) // 2 - graph.num_edges,
                },
            )
        )
    return found


def build(instance: Instance) -> cp_model.CpModel:
    """One Boolean per vertex; non-edges posted as AtMostOne over complement cliques."""
    assert instance.path is not None
    graph = _dimacs.parse_graph(instance.path)
    complement = graph.complement()

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x[{v}]") for v in range(graph.num_vertices)]
    for group in _dimacs.edge_clique_cover(complement):
        model.add_at_most_one(x[v] for v in group)
    model.maximize(sum(x))
    return model


PROBLEM = Problem(
    name="max_clique",
    description="Maximum clique on the DIMACS clique benchmark graphs",
    download=download,
    instances=instances,
    build=build,
    source="https://github.com/jamestrimble/max-weight-clique-instances (DIMACS, weights ignored)",
)

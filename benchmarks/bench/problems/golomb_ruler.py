"""Golomb rulers (CSPLib prob006): minimize the length of the ruler.

Created 2026-09-06 for the CP-SAT log collection. Purpose in the corpus: a tiny
model (a few dozen variables) with a *very* hard optimality proof, so the logs
show long stretches of pure bound improvement with almost no presolve work --
the opposite profile of the large scheduling/routing instances.

Model kind: ``AddAbsEquality`` for every pairwise difference (the textbook
statement "all pairwise absolute differences are distinct") plus one
``AddAllDifferent`` over those differences.

Instances are generated (no download, ``Instance.path is None``); ``meta``
carries the ``order`` (number of marks) and the search bound used.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem

ORDERS = tuple(range(6, 13))

# Known optimal lengths (OEIS A003022) -- only used as a sanity hint in ``meta``.
BEST_KNOWN = {6: 17, 7: 25, 8: 34, 9: 44, 10: 55, 11: 72, 12: 85}


def _upper_bound(order: int) -> int:
    """Safe upper bound on the ruler length: 2^(order-1) is always achievable."""
    return min(2 ** (order - 1), order * order)


def download(data_dir: Path) -> None:
    """Nothing to download: instances are generated from ``meta['order']``."""


def instances(data_dir: Path) -> list[Instance]:
    return [
        Instance(
            name=f"order{order:02d}",
            meta={
                "order": order,
                "num_differences": order * (order - 1) // 2,
                "upper_bound": _upper_bound(order),
                "best_known_length": BEST_KNOWN.get(order),
            },
        )
        for order in sorted(ORDERS)
    ]


def build(instance: Instance) -> cp_model.CpModel:
    order = instance.meta["order"]
    ub = _upper_bound(order)

    model = cp_model.CpModel()
    marks = [model.new_int_var(0, ub, f"m{i}") for i in range(order)]
    model.add(marks[0] == 0)
    for i in range(order - 1):
        model.add(marks[i] < marks[i + 1])

    diffs = []
    for i in range(order):
        for j in range(i + 1, order):
            d = model.new_int_var(1, ub, f"d{i}_{j}")
            # Textbook formulation: the *absolute* difference of every pair of marks.
            model.add_abs_equality(d, marks[j] - marks[i])
            diffs.append(d)
    model.add_all_different(diffs)

    # Redundant: the first k gaps must already cover 1+2+...+k distinct lengths.
    for k in range(1, order):
        model.add(marks[k] >= k * (k + 1) // 2)
        model.add(marks[order - 1] - marks[order - 1 - k] >= k * (k + 1) // 2)

    # Symmetry breaking: the ruler is not equal to its own reversal.
    model.add(marks[1] - marks[0] < marks[order - 1] - marks[order - 2])

    model.minimize(marks[order - 1])
    return model


PROBLEM = Problem(
    name="golomb_ruler",
    description="Golomb ruler (CSPLib prob006) orders 6-12, AbsEquality + AllDifferent, minimize length",
    download=download,
    instances=instances,
    build=build,
    source="https://www.csplib.org/Problems/prob006/",
)

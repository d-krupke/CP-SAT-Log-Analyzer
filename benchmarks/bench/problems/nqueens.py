"""N-queens as a pure satisfaction problem with three AllDifferent constraints.

Created 2026-09-06 for the CP-SAT log collection. Purpose in the corpus: very
large but trivially satisfiable models (n up to 1000 -> 3 AllDifferent over
1000 variables). The logs show what CP-SAT does when the first solution is
found almost immediately and there is no objective at all, plus how presolve
and the LP relaxation react to huge AllDifferent constraints.

Instances are generated (no download, ``Instance.path is None``); ``meta``
carries the board size ``n``.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem

SIZES = (8, 20, 50, 100, 200, 500, 1000)


def download(data_dir: Path) -> None:
    """Nothing to download: instances are generated from ``meta['n']``."""


def instances(data_dir: Path) -> list[Instance]:
    return [
        Instance(name=f"n{n:04d}", meta={"n": n, "num_queens": n, "cells": n * n})
        for n in sorted(SIZES)
    ]


def build(instance: Instance) -> cp_model.CpModel:
    """One variable per row holding the column of its queen.

    ``AddAllDifferent`` on the columns, on ``col + row`` (the "/" diagonals)
    and on ``col - row`` (the "\\" diagonals). Pure satisfaction, no objective.
    """
    n = instance.meta["n"]
    model = cp_model.CpModel()
    cols = [model.new_int_var(0, n - 1, f"q{i}") for i in range(n)]
    model.add_all_different(cols)
    model.add_all_different([cols[i] + i for i in range(n)])
    model.add_all_different([cols[i] - i for i in range(n)])
    # Symmetry breaking: the queen of row 0 stays in the left half of the board.
    model.add(cols[0] <= (n - 1) // 2)
    return model


PROBLEM = Problem(
    name="nqueens",
    description="N-queens satisfaction, n=8..1000, three AllDifferent constraints",
    download=download,
    instances=instances,
    build=build,
    source="generated (classic CSP; see https://www.csplib.org/Problems/prob054/)",
)

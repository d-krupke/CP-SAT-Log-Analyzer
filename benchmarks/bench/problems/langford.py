"""Langford's problem L(2,n) (CSPLib prob024) as a pure satisfaction problem.

Created 2026-09-06 for the CP-SAT log collection. Purpose in the corpus:
satisfaction logs that include *infeasible* runs -- L(2,n) has a solution iff
n = 0 or 3 (mod 4), so n=9,10,17,18 give clean INFEASIBLE logs while
n=8,12,...,32 give SAT logs. Model kind: ``AddElement`` with a *variable*
array (position -> value channelling) plus one ``AddAllDifferent`` over all
2n positions.

Instances are generated (no download, ``Instance.path is None``); ``meta``
carries ``n``, the sequence length ``2n`` and whether a solution exists.
"""

from __future__ import annotations

from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem

SIZES = (8, 9, 10, 12, 16, 17, 18, 20, 24, 28, 32)


def _satisfiable(n: int) -> bool:
    return n % 4 in (0, 3)


def download(data_dir: Path) -> None:
    """Nothing to download: instances are generated from ``meta['n']``."""


def instances(data_dir: Path) -> list[Instance]:
    return [
        Instance(
            name=f"L2_{n:02d}",
            meta={"n": n, "length": 2 * n, "satisfiable": _satisfiable(n)},
        )
        for n in sorted(SIZES)
    ]


def build(instance: Instance) -> cp_model.CpModel:
    """Two position variables per number ``k`` (1..n) that are ``k+1`` apart,
    all 2n positions distinct, and a value variable per position channelled to
    the positions with ``AddElement``.

    ``AddElement(first[k], seq, k + 1)`` reads "the sequence entry at the first
    occurrence of k is k" -- an Element constraint with a variable index *and* a
    variable array, which is exactly the kind of constraint we want in the log
    corpus.
    """
    n = instance.meta["n"]
    length = 2 * n
    model = cp_model.CpModel()

    # seq[p] = the number placed at position p.
    seq = [model.new_int_var(1, n, f"seq{p}") for p in range(length)]

    positions: list[cp_model.IntVar] = []
    for k in range(1, n + 1):
        # The two copies of k are separated by exactly k other entries.
        first = model.new_int_var(0, length - 1 - (k + 1), f"first{k}")
        second = model.new_int_var(k + 1, length - 1, f"second{k}")
        model.add(second == first + k + 1)
        model.add_element(first, seq, k)
        model.add_element(second, seq, k)
        positions += [first, second]

    model.add_all_different(positions)

    # Symmetry breaking: reversing a solution maps the first copy of n from
    # position f to position n-2-f, so we may keep the smaller of the two.
    model.add(2 * positions[-2] <= n - 2)
    return model


PROBLEM = Problem(
    name="langford",
    description="Langford's problem L(2,n) (CSPLib prob024), n=8..32 incl. infeasible n=9,10,17,18",
    download=download,
    instances=instances,
    build=build,
    source="https://www.csplib.org/Problems/prob024/",
)

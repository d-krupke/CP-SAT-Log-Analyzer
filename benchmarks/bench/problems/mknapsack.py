"""Multidimensional (multi-constrained) knapsack from Beasley's OR-Library.

What: one problem class of the CP-SAT log benchmark harness.  Created
2026-09-06 because the MKP is the archetypal "small model, brutal gap" case:
a few hundred Booleans and a handful of dense linear constraints, where CP-SAT
finds a near-optimal solution almost immediately and then spends the whole time
limit on the dual bound.  Ideal for logs dominated by the LP / cut loop.

Source: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html
Files:  https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/mknapcb1.txt etc.
        ``mknap1`` holds 7 small textbook instances, ``mknapcb1..9`` the
        Chu & Beasley set (30 instances each; n in {100, 250, 500} x
        m in {5, 10, 30}, ten instances per tightness ratio 0.25/0.5/0.75).

Format (whitespace separated, line wrapping is irrelevant)::

    P                       number of instances in the file
    for each instance:
        n m opt             items, constraints, optimum (0 = unknown)
        p_1 ... p_n         profits
        w_11 ... w_1n       constraint matrix, m rows of n coefficients
        ...
        b_1 ... b_m         capacities

A few ``mknap1`` instances carry fractional profits/weights; those are scaled to
integers (profits independently, weights together with the capacities).

Model: one Boolean per item, one linear ``<=`` per constraint, maximise profit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files"

# (file, index inside the file).  Ordered easy -> hard: the two largest mknap1
# instances first, then the Chu & Beasley grid by (n, m); inside a file the
# tightness ratio goes 0.75 (index 20) -> 0.5 (10) -> 0.25 (0), i.e. loosest and
# easiest first.
SELECTION: tuple[tuple[str, int], ...] = (
    ("mknap1", 5),
    ("mknap1", 6),
    *((f"mknapcb{f}", k) for f in range(1, 10) for k in (20, 10, 0)),
)
FILES: tuple[str, ...] = ("mknap1", *(f"mknapcb{i}" for i in range(1, 10)))


@dataclass(frozen=True)
class MknapData:
    """One parsed MKP instance with integral coefficients."""

    num_items: int
    num_constraints: int
    profits: list[int]
    weights: list[list[int]]
    capacities: list[int]
    best_known: float | None


def _scale(values: list[Decimal]) -> tuple[list[int], int]:
    """Scale ``values`` by the smallest power of ten that makes them integral."""
    factor = 1
    while any(v * factor != (v * factor).to_integral_value() for v in values):
        factor *= 10
        if factor > 10**6:  # pragma: no cover - no OR-Library file needs this
            raise ValueError("cannot scale coefficients to integers")
    return [int(v * factor) for v in values], factor


def parse_mknap(path: Path) -> list[MknapData]:
    """Parse all instances of one OR-Library ``mknap`` file."""
    tokens = [Decimal(t) for t in path.read_text().split()]
    pos = 0

    def take(count: int) -> list[Decimal]:
        nonlocal pos
        chunk = tokens[pos : pos + count]
        pos += count
        return chunk

    num_problems = int(take(1)[0])
    out: list[MknapData] = []
    for _ in range(num_problems):
        header = take(3)
        n, m, opt = int(header[0]), int(header[1]), float(header[2])
        profits, _ = _scale(take(n))
        rows = [take(n) for _ in range(m)]
        caps = take(m)
        # Weights and capacities must share one scale to preserve feasibility.
        scaled, factor = _scale([v for row in rows for v in row] + list(caps))
        weights = [scaled[i * n : (i + 1) * n] for i in range(m)]
        capacities = scaled[m * n :]
        out.append(MknapData(n, m, profits, weights, capacities, opt or None))
        assert factor >= 1
    if pos != len(tokens):
        raise ValueError(f"{path.name}: {len(tokens) - pos} trailing tokens")
    return out


def download(data_dir: Path) -> None:
    for name in FILES:
        fetch(f"{BASE_URL}/{name}.txt", data_dir / f"{name}.txt")


def instances(data_dir: Path) -> list[Instance]:
    cache: dict[str, list[MknapData]] = {}
    out: list[Instance] = []
    for file_name, index in SELECTION:
        path = data_dir / f"{file_name}.txt"
        if not path.exists():
            continue
        if file_name not in cache:
            cache[file_name] = parse_mknap(path)
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
                    "items": data.num_items,
                    "constraints": data.num_constraints,
                    "best_known": data.best_known,
                },
            )
        )
    return out


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    index = int(instance.meta["index_in_file"])
    data = parse_mknap(instance.path)[index]

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{j}") for j in range(data.num_items)]
    for row, cap in zip(data.weights, data.capacities, strict=True):
        # Zero coefficients only bloat the proto; CP-SAT prefers them dropped.
        terms = [(x[j], w) for j, w in enumerate(row) if w]
        model.add(
            cp_model.LinearExpr.weighted_sum(
                [v for v, _ in terms], [w for _, w in terms]
            )
            <= cap
        )
    model.maximize(cp_model.LinearExpr.weighted_sum(x, data.profits))
    return model


PROBLEM = Problem(
    name="mknapsack",
    description="Multidimensional knapsack (OR-Library mknap1 / Chu & Beasley mknapcb)",
    download=download,
    instances=instances,
    build=build,
    source="https://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html",
)

"""One-dimensional bin packing (minimize the number of bins) for the log harness.

Created 2026-09-06 as one of the problem classes whose CP-SAT search logs feed
the log analyzer.  Bin packing is interesting here because the assignment
formulation is highly symmetric, the LP bound ``ceil(sum/cap)`` is almost always
tight, and the hard families (Schwerin, Scholl "HARD", Hard28) produce logs that
sit for a long time on a one-unit gap -- a very different log shape from
scheduling or routing.

Instances: BPPLIB (Delorme, Iori, Martello),
https://site.unibo.it/operations-research/en/research/bpplib-a-bin-packing-problem-library
The original archives are RAR (not readable with the standard library), so the
files are pulled from pinned GitHub mirrors of the very same BPPLIB text files.

Format of every instance file (BPPLIB "BPP" format), whitespace separated::

    n            number of items
    c            bin capacity
    w_1 ... w_n  one item size per line

Families used, roughly in increasing difficulty: Scholl set 1, Falkenauer U
(uniform) and T (triplets), Waescher, Schwerin, Scholl set 3 ("HARD") and
Hard28.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

SOURCE = (
    "https://site.unibo.it/operations-research/en/research/"
    "bpplib-a-bin-packing-problem-library"
)

# Mirrors with a flat ``datasets/<family>/<file>.txt`` layout (pinned commits).
_FLAT_MIRRORS = (
    (
        "https://raw.githubusercontent.com/b-ikram/OPTIM-Project/"
        "d6fa2416389abfed19ff031b5382b847a798746a/datasets"
    ),
    (
        "https://raw.githubusercontent.com/mounir19000/rl-hgga-bin-packing/"
        "8ab3b4af8b6c98e91a8afa53f4585c2721e64cae/datasets"
    ),
)
# Mirror that keeps the full BPPLIB directory tree (needed for Schwerin/Waescher).
_TREE_MIRROR = (
    "https://raw.githubusercontent.com/dudatsouza/bin-packing-optimization/"
    "77fc0c3838dc754af76d5868b4d1095136d6366c/data/Instances"
)

# (instance name, family label, flat mirror sub-dir or "", tree mirror sub-path or "")
# Ordered by expected difficulty: small/uniform first, Hard28 last.
_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("N1C1W1_A", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("N1C2W2_B", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("Falkenauer_u120_00", "FalkenauerU", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer%20U"),
    ("Falkenauer_u120_19", "FalkenauerU", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer%20U"),
    ("N2C1W1_A", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("N2C2W2_B", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("Falkenauer_t60_00", "FalkenauerT", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer_T"),
    ("Falkenauer_t60_19", "FalkenauerT", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer_T"),
    ("Falkenauer_u250_00", "FalkenauerU", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer%20U"),
    ("Falkenauer_u250_19", "FalkenauerU", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer%20U"),
    ("N3C1W1_A", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("N3C2W2_B", "Scholl1", "Scholl", "2_Scholl/Scholl/Scholl_1"),
    ("Falkenauer_t120_00", "FalkenauerT", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer_T"),
    ("Falkenauer_t120_19", "FalkenauerT", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer_T"),
    ("Falkenauer_u500_00", "FalkenauerU", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer%20U"),
    ("Waescher_TEST0005", "Waescher", "", "3_W%C3%A4scher/W%C3%A4scher"),
    ("Waescher_TEST0014", "Waescher", "", "3_W%C3%A4scher/W%C3%A4scher"),
    ("Falkenauer_t249_00", "FalkenauerT", "Falkenauer", "1_Falkenauer/Falkenauer/Falkenauer_T"),
    ("Schwerin1_BPP1", "Schwerin", "", "4_Schwerin/Schwerin/Schwerin_1"),
    ("Schwerin1_BPP50", "Schwerin", "", "4_Schwerin/Schwerin/Schwerin_1"),
    ("Schwerin2_BPP1", "Schwerin", "", "4_Schwerin/Schwerin/Schwerin_2"),
    ("HARD0", "Scholl3", "Scholl", "2_Scholl/Scholl/Scholl_3"),
    ("HARD5", "Scholl3", "Scholl", "2_Scholl/Scholl/Scholl_3"),
    ("Hard28_BPP13", "Hard28", "Hard28", "5_Hard28/Hard28"),
    ("Hard28_BPP40", "Hard28", "Hard28", "5_Hard28/Hard28"),
    ("Hard28_BPP144", "Hard28", "Hard28", "5_Hard28/Hard28"),
    ("Hard28_BPP645", "Hard28", "Hard28", "5_Hard28/Hard28"),
)


def _candidate_urls(name: str, flat_dir: str, tree_dir: str) -> Iterator[str]:
    if flat_dir:
        for base in _FLAT_MIRRORS:
            yield f"{base}/{flat_dir}/{name}.txt"
    if tree_dir:
        yield f"{_TREE_MIRROR}/{tree_dir}/{name}.txt"


def download(data_dir: Path) -> None:
    """Fetch the selected BPPLIB instance files (~27 files, far below 1 MB)."""
    for name, _family, flat_dir, tree_dir in _SPECS:
        dest = data_dir / f"{name}.txt"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        for url in _candidate_urls(name, flat_dir, tree_dir):
            try:
                fetch(url, dest)
            except Exception as exc:  # noqa: BLE001 - try the next mirror
                print(f"binpacking: {url} failed ({exc})")
                continue
            if dest.exists() and dest.stat().st_size > 0:
                break
        else:
            print(f"binpacking: could not download {name}")


def _read(path: Path) -> tuple[int, list[int]]:
    """Parse a BPPLIB BPP file into ``(capacity, item sizes)``."""
    tokens = path.read_text(encoding="utf-8", errors="replace").split()
    n, capacity = int(tokens[0]), int(tokens[1])
    sizes = [int(float(t)) for t in tokens[2 : 2 + n]]
    if len(sizes) != n:
        raise ValueError(f"{path}: expected {n} item sizes, found {len(sizes)}")
    return capacity, sizes


def _first_fit_decreasing(sizes: list[int], capacity: int) -> int:
    """Number of bins used by first-fit-decreasing; a valid upper bound."""
    remaining: list[int] = []
    for size in sorted(sizes, reverse=True):
        for i, free in enumerate(remaining):
            if free >= size:
                remaining[i] = free - size
                break
        else:
            remaining.append(capacity - size)
    return len(remaining)


def instances(data_dir: Path) -> list[Instance]:
    result: list[Instance] = []
    for name, family, _flat, _tree in _SPECS:
        path = data_dir / f"{name}.txt"
        if not path.exists():
            continue
        capacity, sizes = _read(path)
        total = sum(sizes)
        result.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "family": family,
                    "items": len(sizes),
                    "capacity": capacity,
                    "total_size": total,
                    "lb_bins": math.ceil(total / capacity),
                    "ffd_bins": _first_fit_decreasing(sizes, capacity),
                },
            )
        )
    return result


def build(instance: Instance) -> cp_model.CpModel:
    """Assignment formulation: x[item, bin], y[bin], minimize the bins used.

    Items are sorted by decreasing size so that the canonical-labeling
    symmetry break "item ``i`` may only sit in bins ``0..i``" applies, which is
    combined with ``y[b] >= y[b+1]`` (bins are filled from index 0).  Both hold
    simultaneously in the packing obtained by relabeling bins by their
    smallest item index, so no optimal solution is lost.
    """
    assert instance.path is not None
    capacity, sizes = _read(instance.path)
    sizes.sort(reverse=True)
    n = len(sizes)
    n_bins = _first_fit_decreasing(sizes, capacity)
    lb_bins = math.ceil(sum(sizes) / capacity)

    model = cp_model.CpModel()
    # x[i, b] == 1 <=> item i is packed into bin b (only b <= i is allowed).
    bins_of = [range(min(i + 1, n_bins)) for i in range(n)]
    x = {
        (i, b): model.new_bool_var(f"x_{i}_{b}") for i in range(n) for b in bins_of[i]
    }
    y = [model.new_bool_var(f"y_{b}") for b in range(n_bins)]

    for i in range(n):
        model.add_exactly_one(x[i, b] for b in bins_of[i])
    for b in range(n_bins):
        load = sum(sizes[i] * x[i, b] for i in range(b, n) if (i, b) in x)
        model.add(load <= capacity * y[b])
    for b in range(n_bins - 1):
        model.add(y[b] >= y[b + 1])

    bins_used = model.new_int_var(lb_bins, n_bins, "bins_used")
    model.add(bins_used == sum(y))
    model.minimize(bins_used)
    return model


PROBLEM = Problem(
    name="binpacking",
    description="1D bin packing (BPPLIB: Falkenauer, Scholl, Waescher, Schwerin, Hard28)",
    download=download,
    instances=instances,
    build=build,
    source=SOURCE,
)

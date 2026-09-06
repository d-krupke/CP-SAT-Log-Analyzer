"""Sudoku as a pure satisfaction problem (AllDifferent only).

Created 2026-09-06 for the CP-SAT log collection: gives the analyzer logs of
*feasibility* runs (no objective, no bound improvements) that are dominated by
propagation on ``AddAllDifferent``.

Instances
---------
* 9x9: Peter Norvig's classic hard puzzle lists ``top95.txt`` and
  ``hardest.txt`` (https://norvig.com/sudoku.html). norvig.com is behind a
  bot-challenge, so we fetch the verbatim mirrors in
  https://github.com/dimitri/sudoku. Format: one puzzle per line, 81
  characters row-major, ``.`` or ``0`` for an empty cell.
* 16x16 and 25x25: generated (``path is None``); ``meta`` carries ``order``,
  ``seed`` and ``keep`` and ``build`` regenerates the puzzle deterministically
  by permuting a solved base grid and dropping clues with a seeded RNG.
"""

from __future__ import annotations

import random
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

MIRROR = "https://raw.githubusercontent.com/dimitri/sudoku/master"
LISTS = ("top95.txt", "hardest.txt")
NUM_FROM_TOP95 = 12  # + the 11 puzzles of hardest.txt -> 23 classic 9x9 puzzles

# order (box side), seed, fraction of cells kept as clues
GENERATED = ((4, 20260906, 0.40), (4, 424242, 0.36), (5, 20260906, 0.45))


def download(data_dir: Path) -> None:
    for name in LISTS:
        fetch(f"{MIRROR}/{name}", data_dir / name)


def _puzzles(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if len(line) == 81:
            out.append(line)
    return out


def instances(data_dir: Path) -> list[Instance]:
    out: list[Instance] = []
    for name, take in zip(LISTS, (NUM_FROM_TOP95, 99), strict=True):
        path = data_dir / name
        if not path.exists():
            continue
        for i, puzzle in enumerate(_puzzles(path)[:take]):
            givens = sum(ch not in ".0" for ch in puzzle)
            out.append(
                Instance(
                    name=f"{path.stem}_{i:02d}",
                    path=path,
                    meta={"order": 3, "size": 9, "cells": 81, "givens": givens, "line": i},
                )
            )
    for order, seed, keep in GENERATED:
        side = order * order
        out.append(
            Instance(
                name=f"gen{side}x{side}_s{seed}",
                meta={
                    "order": order,
                    "size": side,
                    "cells": side * side,
                    "seed": seed,
                    "keep": keep,
                    "givens": round(keep * side * side),
                },
            )
        )
    # 9x9 first (tiny models), then the generated large grids by size
    out.sort(key=lambda inst: (inst.meta["size"], inst.name))
    return out


def _solved_grid(order: int, rng: random.Random) -> list[list[int]]:
    """A random valid solution: base pattern + band/stack/row/column/label shuffles."""
    side = order * order
    base = [[(order * (r % order) + r // order + c) % side + 1 for c in range(side)] for r in range(side)]

    def shuffled_index() -> list[int]:
        blocks = list(range(order))
        rng.shuffle(blocks)
        idx: list[int] = []
        for b in blocks:
            inner = [b * order + k for k in range(order)]
            rng.shuffle(inner)
            idx.extend(inner)
        return idx

    rows, cols = shuffled_index(), shuffled_index()
    labels = list(range(1, side + 1))
    rng.shuffle(labels)
    return [[labels[base[r][c] - 1] for c in cols] for r in rows]


def _generated_puzzle(order: int, seed: int, keep: float) -> list[list[int]]:
    """Solved grid with a deterministic set of clues kept (0 = empty)."""
    rng = random.Random(seed)
    grid = _solved_grid(order, rng)
    side = order * order
    cells = [(r, c) for r in range(side) for c in range(side)]
    rng.shuffle(cells)
    for r, c in cells[round(keep * len(cells)) :]:
        grid[r][c] = 0
    return grid


def _grid(instance: Instance) -> list[list[int]]:
    if instance.path is None:
        return _generated_puzzle(instance.meta["order"], instance.meta["seed"], instance.meta["keep"])
    puzzle = _puzzles(instance.path)[instance.meta["line"]]
    return [[0 if ch in ".0" else int(ch) for ch in puzzle[r * 9 : r * 9 + 9]] for r in range(9)]


def build(instance: Instance) -> cp_model.CpModel:
    order = instance.meta["order"]
    side = order * order
    grid = _grid(instance)

    model = cp_model.CpModel()
    x = [[model.new_int_var(1, side, f"x{r}_{c}") for c in range(side)] for r in range(side)]
    for r in range(side):
        for c in range(side):
            if grid[r][c]:
                model.add(x[r][c] == grid[r][c])
    for r in range(side):
        model.add_all_different(x[r])
    for c in range(side):
        model.add_all_different([x[r][c] for r in range(side)])
    for br in range(order):
        for bc in range(order):
            model.add_all_different(
                [x[br * order + i][bc * order + j] for i in range(order) for j in range(order)]
            )
    return model


PROBLEM = Problem(
    name="sudoku",
    description="Sudoku satisfaction (9x9 hard lists + generated 16x16/25x25), AllDifferent only",
    download=download,
    instances=instances,
    build=build,
    source="https://norvig.com/sudoku.html (mirror: https://github.com/dimitri/sudoku)",
)

"""Two-dimensional strip packing (minimize the strip height) for the log harness.

Created 2026-09-06 as one of the problem classes whose CP-SAT search logs feed
the log analyzer.  Strip packing is the showcase for ``add_no_overlap_2d``: the
logs are dominated by the scheduling propagators and by the "energetic" LP
relaxation, and the classic perfect-packing families (Hopper & Turton C, Burke
N/T) have an area lower bound that equals the optimum, so the interesting part
of the log is how long CP-SAT needs to *reach* that bound.

Instances: 2DPackLib (Iori, de Lima, Martello, Monaci),
https://site.unibo.it/operations-research/en/research/2dpacklib
Sets used: ``C`` (Hopper & Turton), ``N_T`` (Burke et al. / Wang & Valenzuela)
and ``BENG`` (Bengtsson).  All three are small ZIP archives.

Format of an ``.ins2D`` file (whitespace separated)::

    m                          number of items
    W H                        strip width, reference height (-1 if unknown)
    i w_i h_i d_i b_i p_i      one line per item (id, width, height, demand,
                               max copies, profit)

Only ``W`` and the ``(w_i, h_i)`` pairs are used; every item is packed exactly
once and rotation is not allowed.
"""

from __future__ import annotations

import math
import zipfile
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

SOURCE = "https://site.unibo.it/operations-research/en/research/2dpacklib"

_BASE = "https://site.unibo.it/operations-research/en/research/2dpacklib"
_ARCHIVES = (("c", "C"), ("n_t", "N_T"), ("beng", "BENG"))

# Ordered by expected difficulty (item count, then family).
_NAMES: tuple[tuple[str, str], ...] = (
    ("c1-p1", "HopperTurton"),
    ("c1-p2", "HopperTurton"),
    ("N1a", "Burke-N"),
    ("T1a", "Burke-T"),
    ("BENG01", "Bengtsson"),
    ("c2-p1", "HopperTurton"),
    ("N2a", "Burke-N"),
    ("c3-p1", "HopperTurton"),
    ("BENG02", "Bengtsson"),
    ("N3a", "Burke-N"),
    ("BENG06", "Bengtsson"),
    ("c4-p1", "HopperTurton"),
    ("N4a", "Burke-N"),
    ("c5-p1", "HopperTurton"),
    ("N5a", "Burke-N"),
    ("BENG05", "Bengtsson"),
    ("c6-p1", "HopperTurton"),
    ("BENG10", "Bengtsson"),
    ("c7-p1", "HopperTurton"),
    ("N7a", "Burke-N"),
)
_WANTED = frozenset(name for name, _ in _NAMES)


def download(data_dir: Path) -> None:
    """Fetch the three 2DPackLib archives (< 100 kB) and flatten the wanted files."""
    for slug, label in _ARCHIVES:
        archive = data_dir / f"{label}.zip"
        fetch(f"{_BASE}/{slug}.zip/@@download/file/{label}.zip", archive)
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                stem = Path(member).stem
                if not member.endswith(".ins2D") or stem not in _WANTED:
                    continue
                dest = data_dir / f"{stem}.ins2D"
                if dest.exists() and dest.stat().st_size > 0:
                    continue
                dest.write_bytes(zf.read(member))


def _read(path: Path) -> tuple[int, list[tuple[int, int]]]:
    """Parse an ``.ins2D`` file into ``(strip width, [(w, h), ...])``."""
    tokens = path.read_text(encoding="utf-8", errors="replace").split()
    m, width = int(tokens[0]), int(tokens[1])
    rows = tokens[3:]
    rects = [(int(rows[6 * i + 1]), int(rows[6 * i + 2])) for i in range(m)]
    return width, rects


def _shelf_height(rects: list[tuple[int, int]], width: int) -> int:
    """Height of a first-fit-decreasing-height shelf packing; a valid upper bound."""
    shelves: list[int] = []  # remaining width per shelf
    total = 0
    for w, h in sorted(rects, key=lambda r: -r[1]):
        for i, free in enumerate(shelves):
            if free >= w:
                shelves[i] = free - w
                break
        else:
            shelves.append(width - w)
            total += h
    return total


def _bounds(rects: list[tuple[int, int]], width: int) -> tuple[int, int]:
    area = sum(w * h for w, h in rects)
    lower = max(math.ceil(area / width), max(h for _, h in rects))
    return lower, max(lower, _shelf_height(rects, width))


def instances(data_dir: Path) -> list[Instance]:
    result: list[Instance] = []
    for name, family in _NAMES:
        path = data_dir / f"{name}.ins2D"
        if not path.exists():
            continue
        width, rects = _read(path)
        lower, upper = _bounds(rects, width)
        result.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "family": family,
                    "items": len(rects),
                    "width": width,
                    "area": sum(w * h for w, h in rects),
                    "lb_height": lower,
                    "ub_height": upper,
                },
            )
        )
    return result


def build(instance: Instance) -> cp_model.CpModel:
    """Interval model: one x- and one y-interval per rectangle, no-overlap-2d.

    The objective ``height`` bounds every y-interval from above.  Two redundant
    ``add_cumulative`` constraints give the LP relaxation the area ("energetic")
    argument in both directions: widths over the y-axis against the fixed strip
    width, and heights over the x-axis against the variable height.
    """
    assert instance.path is not None
    width, rects = _read(instance.path)
    lower, upper = _bounds(rects, width)

    model = cp_model.CpModel()
    height = model.new_int_var(lower, upper, "height")
    x_intervals, y_intervals = [], []
    for i, (w, h) in enumerate(rects):
        x_start = model.new_int_var(0, width - w, f"x_{i}")
        y_start = model.new_int_var(0, upper - h, f"y_{i}")
        x_intervals.append(model.new_fixed_size_interval_var(x_start, w, f"ix_{i}"))
        y_intervals.append(model.new_fixed_size_interval_var(y_start, h, f"iy_{i}"))
        model.add(y_start + h <= height)

    model.add_no_overlap_2d(x_intervals, y_intervals)
    model.add_cumulative(y_intervals, [w for w, _ in rects], width)
    model.add_cumulative(x_intervals, [h for _, h in rects], height)
    model.minimize(height)
    return model


PROBLEM = Problem(
    name="strip_packing",
    description="2D strip packing, minimize height (2DPackLib: Hopper&Turton C, Burke N/T, BENG)",
    download=download,
    instances=instances,
    build=build,
    source=SOURCE,
)

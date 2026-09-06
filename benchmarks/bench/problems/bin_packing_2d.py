"""Two-dimensional bin packing (minimize the number of bins) for the log harness.

Created 2026-09-06 as one of the problem classes whose CP-SAT search logs feed
the log analyzer.  Compared to ``strip_packing`` this model mixes geometry with
a combinatorial "how many bins" decision, so the logs show a much more active
objective-bound race and a lot of no-overlap-2d propagation on a wide virtual
strip -- a log shape that neither pure scheduling nor pure assignment produces.

Instances: 2DPackLib (Iori, de Lima, Martello, Monaci), ``CLASS`` set,
https://site.unibo.it/operations-research/en/research/2dpacklib
Classes 1-6 are Berkey & Wang, classes 7-10 are Martello & Vigo; only the small
20- and 40-item instances are used.

Format of an ``.ins2D`` file (whitespace separated)::

    m                          number of items
    W H                        bin width and height
    i w_i h_i d_i b_i p_i      one line per item (id, width, height, demand,
                               max copies, profit)

Only ``W``, ``H`` and the ``(w_i, h_i)`` pairs are used; every item is packed
exactly once and rotation is not allowed.
"""

from __future__ import annotations

import math
import zipfile
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

SOURCE = "https://site.unibo.it/operations-research/en/research/2dpacklib"

_ARCHIVE_URL = (
    "https://site.unibo.it/operations-research/en/research/2dpacklib/"
    "class.zip/@@download/file/CLASS.zip"
)

# Ordered by expected difficulty (bins in the area bound, then item count).
_NAMES: tuple[tuple[str, str], ...] = (
    ("cl_02_020_01", "BerkeyWang"),
    ("cl_04_020_01", "BerkeyWang"),
    ("cl_06_020_01", "BerkeyWang"),
    ("cl_03_020_01", "BerkeyWang"),
    ("cl_07_020_01", "MartelloVigo"),
    ("cl_08_020_01", "MartelloVigo"),
    ("cl_05_020_01", "BerkeyWang"),
    ("cl_10_020_01", "MartelloVigo"),
    ("cl_01_020_01", "BerkeyWang"),
    ("cl_09_020_01", "MartelloVigo"),
    ("cl_03_040_01", "BerkeyWang"),
    ("cl_05_040_01", "BerkeyWang"),
    ("cl_01_040_01", "BerkeyWang"),
    ("cl_09_040_01", "MartelloVigo"),
)
_WANTED = frozenset(name for name, _ in _NAMES)


def download(data_dir: Path) -> None:
    """Fetch the 2DPackLib CLASS archive (~240 kB) and flatten the wanted files."""
    archive = data_dir / "CLASS.zip"
    fetch(_ARCHIVE_URL, archive)
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            stem = Path(member).stem
            if not member.endswith(".ins2D") or stem not in _WANTED:
                continue
            dest = data_dir / f"{stem}.ins2D"
            if dest.exists() and dest.stat().st_size > 0:
                continue
            dest.write_bytes(zf.read(member))


def _read(path: Path) -> tuple[int, int, list[tuple[int, int]]]:
    """Parse an ``.ins2D`` file into ``(bin width, bin height, [(w, h), ...])``."""
    tokens = path.read_text(encoding="utf-8", errors="replace").split()
    m, width, height = int(tokens[0]), int(tokens[1]), int(tokens[2])
    rows = tokens[3:]
    rects = [(int(rows[6 * i + 1]), int(rows[6 * i + 2])) for i in range(m)]
    return width, height, rects


def _shelf_bins(rects: list[tuple[int, int]], width: int, height: int) -> int:
    """Bins used by a shelf (FFDH) heuristic across bins; a valid upper bound."""
    bins: list[tuple[list[int], list[int]]] = []  # (shelf free widths, [used height])
    for w, h in sorted(rects, key=lambda r: -r[1]):
        for free_widths, used in bins:
            placed = False
            for i, free in enumerate(free_widths):
                if free >= w:
                    free_widths[i] = free - w
                    placed = True
                    break
            if placed:
                break
            if used[0] + h <= height:
                free_widths.append(width - w)
                used[0] += h
                break
        else:
            bins.append(([width - w], [h]))
    return len(bins)


def _bounds(rects: list[tuple[int, int]], width: int, height: int) -> tuple[int, int]:
    area = sum(w * h for w, h in rects)
    lower = max(1, math.ceil(area / (width * height)))
    return lower, max(lower, _shelf_bins(rects, width, height))


def instances(data_dir: Path) -> list[Instance]:
    result: list[Instance] = []
    for name, family in _NAMES:
        path = data_dir / f"{name}.ins2D"
        if not path.exists():
            continue
        width, height, rects = _read(path)
        lower, upper = _bounds(rects, width, height)
        result.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "family": family,
                    "items": len(rects),
                    "bin_width": width,
                    "bin_height": height,
                    "lb_bins": lower,
                    "ub_bins": upper,
                },
            )
        )
    return result


def build(instance: Instance) -> cp_model.CpModel:
    """Virtual-strip formulation: all bins side by side in one strip of width ``B*W``.

    Item ``i`` gets a bin index ``bin[i]`` and an x-position confined to
    ``[bin[i]*W, bin[i]*W + W - w_i]``, so no rectangle can straddle a bin
    border and a single ``add_no_overlap_2d`` over the whole strip enforces
    intra-bin disjointness.  Items are sorted by decreasing area and restricted
    to ``bin[i] <= i`` (canonical relabeling of the interchangeable bins).
    Redundant cumulative constraints add the area argument along both axes.
    """
    assert instance.path is not None
    width, height, rects = _read(instance.path)
    rects.sort(key=lambda r: -r[0] * r[1])
    lower, upper = _bounds(rects, width, height)

    model = cp_model.CpModel()
    n_bins = model.new_int_var(lower, upper, "n_bins")
    bin_of, x_intervals, y_intervals = [], [], []
    for i, (w, h) in enumerate(rects):
        b = model.new_int_var(0, min(i, upper - 1), f"bin_{i}")
        x_start = model.new_int_var(0, upper * width - w, f"x_{i}")
        y_start = model.new_int_var(0, height - h, f"y_{i}")
        model.add(x_start >= width * b)
        model.add(x_start + w <= width * b + width)
        bin_of.append(b)
        x_intervals.append(model.new_fixed_size_interval_var(x_start, w, f"ix_{i}"))
        y_intervals.append(model.new_fixed_size_interval_var(y_start, h, f"iy_{i}"))

    model.add_no_overlap_2d(x_intervals, y_intervals)
    # At any x the stacked heights fit into one bin height; at any y the widths
    # fit into the total width of the bins that are actually used.
    model.add_cumulative(x_intervals, [h for _, h in rects], height)
    model.add_cumulative(y_intervals, [w for w, _ in rects], width * n_bins)
    model.add_max_equality(n_bins - 1, bin_of)
    model.minimize(n_bins)
    return model


PROBLEM = Problem(
    name="bin_packing_2d",
    description="2D bin packing, minimize bins (2DPackLib CLASS: Berkey&Wang, Martello&Vigo)",
    download=download,
    instances=instances,
    build=build,
    source=SOURCE,
)

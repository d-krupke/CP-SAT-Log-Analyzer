"""Minimal TSPLIB95 reader shared by the ``tsp`` and ``cvrp`` problem modules.

Created 2026-09-06 for the CP-SAT log benchmark harness: both problem classes
use instance files in the TSPLIB95 text format, so the parsing and the official
distance rounding rules live here once instead of twice.

Format reference: TSPLIB95 documentation (Reinelt),
http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp95.pdf

Supported: ``NODE_COORD_SECTION``, ``EDGE_WEIGHT_SECTION``, ``DEMAND_SECTION``,
``DEPOT_SECTION``; edge weight types ``EUC_2D``, ``CEIL_2D``, ``ATT``, ``GEO``
and ``EXPLICIT`` with formats ``FULL_MATRIX``, ``UPPER_ROW``, ``LOWER_ROW``,
``UPPER_DIAG_ROW`` and ``LOWER_DIAG_ROW``. Files may be gzip-compressed
(``.gz`` suffix). Module name starts with ``_`` so the problem registry in
``bench/problems/__init__.py`` skips it.

Change it when a new instance family needs another section or weight type; keep
the rounding rules byte-identical to TSPLIB, otherwise objective values cannot
be compared against published optima.
"""

from __future__ import annotations

import gzip
import math
from dataclasses import dataclass
from pathlib import Path

_SECTIONS = {
    "NODE_COORD_SECTION",
    "EDGE_WEIGHT_SECTION",
    "DEMAND_SECTION",
    "DEPOT_SECTION",
    "DISPLAY_DATA_SECTION",
    "FIXED_EDGES_SECTION",
    "TOUR_SECTION",
    "EOF",
}


@dataclass(frozen=True)
class TsplibInstance:
    """One parsed TSPLIB file (a TSP, ATSP or CVRP instance)."""

    name: str
    dimension: int
    problem_type: str  # TSP / ATSP / CVRP
    edge_weight_type: str
    coords: list[tuple[float, float]]
    weights: list[list[int]]  # empty unless EDGE_WEIGHT_TYPE is EXPLICIT
    demands: list[int]  # empty for pure routing instances
    depot: int  # 0-based
    capacity: int | None

    @property
    def symmetric(self) -> bool:
        return self.problem_type.upper() != "ATSP"


def read_text(path: Path) -> str:
    """Read a plain or gzip-compressed TSPLIB file."""
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
    return path.read_text(encoding="utf-8", errors="replace")


def parse(path: Path) -> TsplibInstance:
    """Parse a TSPLIB file into a :class:`TsplibInstance`."""
    spec: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line:
            continue
        head = line.split(":", 1)[0].strip().upper()
        if head in _SECTIONS:
            current = head
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            sections[current] = [rest] if rest else []
            continue
        if ":" in line and current is None:
            key, value = line.split(":", 1)
            spec[key.strip().upper()] = value.strip()
            continue
        if current is None:
            # Keyword lines without a colon ("DIMENSION 42") appear in the wild.
            parts = line.split()
            if len(parts) >= 2 and parts[0].upper() in {"NAME", "TYPE", "DIMENSION", "CAPACITY"}:
                spec[parts[0].upper()] = " ".join(parts[1:])
            continue
        sections[current].append(line)

    dimension = int(spec["DIMENSION"].split()[0])
    ewt = spec.get("EDGE_WEIGHT_TYPE", "EUC_2D").upper()
    coords = _parse_coords(sections.get("NODE_COORD_SECTION", []), dimension)
    weights: list[list[int]] = []
    if ewt == "EXPLICIT":
        fmt = spec.get("EDGE_WEIGHT_FORMAT", "FULL_MATRIX").upper()
        weights = _parse_matrix(sections.get("EDGE_WEIGHT_SECTION", []), dimension, fmt)
    demands = _parse_demands(sections.get("DEMAND_SECTION", []), dimension)
    depot_lines = sections.get("DEPOT_SECTION", [])
    depot = 0
    for line in depot_lines:
        first = int(float(line.split()[0]))
        if first > 0:
            depot = first - 1
            break
    capacity = int(float(spec["CAPACITY"].split()[0])) if "CAPACITY" in spec else None
    return TsplibInstance(
        name=_clean_name(spec.get("NAME", path.stem)),
        dimension=dimension,
        problem_type=spec.get("TYPE", "TSP").split()[0].upper(),
        edge_weight_type=ewt,
        coords=coords,
        weights=weights,
        demands=demands,
        depot=depot,
        capacity=capacity,
    )


def _clean_name(value: str) -> str:
    """NAME fields sometimes carry the file extension (``ulysses16.tsp``)."""
    token = value.split()[0] if value.split() else value
    for suffix in (".tsp", ".atsp", ".vrp"):
        if token.lower().endswith(suffix):
            return token[: -len(suffix)]
    return token


def read_dimension(path: Path) -> int:
    """Cheap header peek: the ``DIMENSION`` of an instance without full parsing."""
    for raw in read_text(path).splitlines():
        parts = raw.replace(":", " ").split()
        if parts and parts[0].upper() == "DIMENSION":
            return int(float(parts[1]))
    raise ValueError(f"no DIMENSION in {path}")


def _numbers(lines: list[str]) -> list[float]:
    out: list[float] = []
    for line in lines:
        for token in line.replace(",", " ").split():
            try:
                out.append(float(token))
            except ValueError:
                continue
    return out


def _parse_coords(lines: list[str], n: int) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            coords.append((float(parts[1]), float(parts[2])))
    return coords[:n]


def _parse_demands(lines: list[str], n: int) -> list[int]:
    demands = [0] * n
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            demands[int(float(parts[0])) - 1] = int(float(parts[1]))
    return demands if lines else []


def _parse_matrix(lines: list[str], n: int, fmt: str) -> list[list[int]]:
    values = [round(v) for v in _numbers(lines)]
    m = [[0] * n for _ in range(n)]
    it = iter(values)

    def take() -> int:
        return next(it)

    if fmt == "FULL_MATRIX":
        for i in range(n):
            for j in range(n):
                m[i][j] = take()
        return m
    if fmt in {"UPPER_ROW", "UPPER_DIAG_ROW"}:
        for i in range(n):
            for j in range(i if fmt == "UPPER_DIAG_ROW" else i + 1, n):
                m[i][j] = m[j][i] = take()
        return m
    if fmt in {"LOWER_ROW", "LOWER_DIAG_ROW"}:
        for i in range(n):
            for j in range(i + 1 if fmt == "LOWER_DIAG_ROW" else i):
                m[i][j] = m[j][i] = take()
        return m
    raise ValueError(f"unsupported EDGE_WEIGHT_FORMAT {fmt}")


def _geo_radians(value: float) -> float:
    deg = int(value)
    minutes = value - deg
    return math.pi * (deg + 5.0 * minutes / 3.0) / 180.0


def distance_matrix(inst: TsplibInstance) -> list[list[int]]:
    """Integer distances following the official TSPLIB rounding rules."""
    n = inst.dimension
    if inst.edge_weight_type == "EXPLICIT":
        if not inst.weights:
            raise ValueError(f"{inst.name}: EXPLICIT but no EDGE_WEIGHT_SECTION")
        return inst.weights
    if len(inst.coords) < n:
        raise ValueError(f"{inst.name}: expected {n} coordinates, got {len(inst.coords)}")
    ewt = inst.edge_weight_type
    if ewt == "GEO":
        lat = [_geo_radians(x) for x, _ in inst.coords]
        lon = [_geo_radians(y) for _, y in inst.coords]
    m = [[0] * n for _ in range(n)]
    for i in range(n):
        xi, yi = inst.coords[i]
        for j in range(i + 1, n):
            xj, yj = inst.coords[j]
            if ewt in {"EUC_2D", "CEIL_2D", "ATT"}:
                dx, dy = xi - xj, yi - yj
                if ewt == "EUC_2D":
                    d = int(math.sqrt(dx * dx + dy * dy) + 0.5)
                elif ewt == "CEIL_2D":
                    d = math.ceil(math.sqrt(dx * dx + dy * dy))
                else:
                    r = math.sqrt((dx * dx + dy * dy) / 10.0)
                    t = int(r + 0.5)
                    d = t + 1 if t < r else t
            elif ewt == "GEO":
                rrr = 6378.388
                q1 = math.cos(lon[i] - lon[j])
                q2 = math.cos(lat[i] - lat[j])
                q3 = math.cos(lat[i] + lat[j])
                d = int(rrr * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)
            else:
                raise ValueError(f"unsupported EDGE_WEIGHT_TYPE {ewt}")
            m[i][j] = m[j][i] = d
    return m

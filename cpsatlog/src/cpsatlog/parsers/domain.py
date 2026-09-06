"""Structured view of a variable-domain line of the model description.

Created for the model-card indicators of the v2 analyzer (domain size, holes).
CP-SAT prints one line per distinct domain, e.g. ``3'000 Booleans in [0,1]``,
``20 in [0,10]``, ``5 in [0][10][20]`` (holes), ``4 constants in {0,1}`` or, when
there are too many domains, ``132 different domains in [0,12864] with a
largest complexity of 1.``. Lines longer than ~105 characters are truncated by
the solver with `` ... `` in the middle; then only the outer bounds are known.

Pure function, no I/O; ``ModelParser`` calls :func:`parse_domain` for every
domain line and stores the result in ``DomainLine``.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from ..text import NUMBER_TOKEN, parse_int

DomainKind = Literal["bool", "int", "constant", "summary", "other"]

_INTERVAL = re.compile(rf"\[(?P<lo>{NUMBER_TOKEN})(?:,(?P<hi>{NUMBER_TOKEN}))?\]")
_SUMMARY = re.compile(
    rf"different domains in \[(?P<lo>{NUMBER_TOKEN}),(?P<hi>{NUMBER_TOKEN})\]"
    rf"(?: with a largest complexity of (?P<cx>{NUMBER_TOKEN}))?"
)
_SET = re.compile(r"constants in \{(?P<body>.*)\}")
_TRUNCATED = " ... "


class DomainInfo(TypedDict):
    kind: DomainKind
    lo: int | None
    hi: int | None
    size: int | None
    intervals: int | None
    truncated: bool


def parse_domain(description: str) -> DomainInfo:
    """Parse the text after the count of a domain line (``'Booleans in [0,1]'``)."""
    desc = description.strip()
    truncated = _TRUNCATED in desc
    info = DomainInfo(
        kind="other", lo=None, hi=None, size=None, intervals=None, truncated=truncated
    )
    if m := _SUMMARY.search(desc):
        info["kind"] = "summary"
        info["lo"], info["hi"] = parse_int(m.group("lo")), parse_int(m.group("hi"))
        info["intervals"] = parse_int(m.group("cx")) if m.group("cx") else None
        return info
    if m := _SET.search(desc):
        info["kind"] = "constant"
        values = [parse_int(v) for v in m.group("body").replace(_TRUNCATED, ",").split(",")]
        known = [v for v in values if v is not None]
        if known:
            info["lo"], info["hi"] = min(known), max(known)
        if not truncated:
            info["size"], info["intervals"] = len(known), len(known)
        return info
    intervals = list(_INTERVAL.finditer(desc))
    if not intervals:
        return info
    bounds = [
        (parse_int(i.group("lo")), parse_int(i.group("hi") or i.group("lo"))) for i in intervals
    ]
    los = [lo for lo, _ in bounds if lo is not None]
    his = [hi for _, hi in bounds if hi is not None]
    info["lo"], info["hi"] = (min(los) if los else None), (max(his) if his else None)
    if not truncated and all(lo is not None and hi is not None for lo, hi in bounds):
        info["size"] = sum(hi - lo + 1 for lo, hi in bounds if lo is not None and hi is not None)
        info["intervals"] = len(bounds)
    info["kind"] = "bool" if desc.startswith("Boolean") else "int"
    return info

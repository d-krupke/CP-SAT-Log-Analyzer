"""Parser for ``CpSolverResponse summary:`` (and the preceding ``LRAT_status`` line)."""

from __future__ import annotations

import re

from ..schema.base import LineSpan, Loc
from ..schema.response import ResponseSummary
from ..splitter import Chunk
from ..text import parse_float, parse_int
from .base import BlockParser

_HEADER = re.compile(r"^(?:CpSolverResponse summary:|LRAT_status:)")
_KV = re.compile(r"^(?P<key>[A-Za-z_]+):\s*(?P<value>.*)$")

_INT_FIELDS = {
    "integers",
    "booleans",
    "conflicts",
    "branches",
    "propagations",
    "integer_propagations",
    "restarts",
    "lp_iterations",
}
_FLOAT_FIELDS = {
    "objective",
    "best_bound",
    "walltime",
    "usertime",
    "deterministic_time",
    "gap_integral",
}
_STR_FIELDS = {"status", "solution_fingerprint"}


class ResponseParser(BlockParser):
    kind = "response"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return bool(_HEADER.match(chunk.first))

    @classmethod
    def parse(cls, chunk: Chunk) -> ResponseSummary:
        response = ResponseSummary(span=LineSpan(start=chunk.start, end=chunk.end))
        for no, line in chunk.numbered():
            if line.startswith("CpSolverResponse summary:"):
                continue
            m = _KV.match(line)
            if not m:
                response.extra[f"line_{no}"] = Loc(value=line, line=no)
                continue
            key, value = m.group("key"), m.group("value").strip()
            if key == "CpSolverResponse":
                continue
            if key == "LRAT_status":
                response.lrat_status = Loc(value=value, line=no)
            elif key in _INT_FIELDS:
                num = parse_int(value)
                if num is not None:
                    setattr(response, key, Loc(value=num, line=no))
            elif key in _FLOAT_FIELDS:
                num = parse_float(value)
                if num is not None:
                    setattr(response, key, Loc(value=num, line=no))
            elif key in _STR_FIELDS:
                setattr(response, key, Loc(value=value, line=no))
            else:
                response.extra[key] = Loc(value=value, line=no)
        return response

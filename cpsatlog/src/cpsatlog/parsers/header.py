"""Parser for the log header (version, parameters, worker count)."""

from __future__ import annotations

import re

from ..schema.base import LineSpan, Loc
from ..schema.solver import SolverInfo
from ..splitter import Chunk
from .base import BlockParser
from .parameters import parse_parameters

_VERSION = re.compile(
    r"^Starting CP-SAT solver v(?P<v>(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))"
)
_PARAMS = re.compile(r"^Parameters:\s*(?P<rest>.*)$")
_WORKERS = re.compile(r"^Setting number of workers to (?P<n>\d+)")
_SHARED_TREE = re.compile(r"^Setting number of shared tree workers to (?P<n>\d+)")


class SolverParser(BlockParser):
    kind = "solver"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return bool(
            _VERSION.match(chunk.first)
            or _PARAMS.match(chunk.first)
            or _WORKERS.match(chunk.first)
            or _SHARED_TREE.match(chunk.first)
        )

    @classmethod
    def parse(cls, chunk: Chunk) -> SolverInfo:
        info = SolverInfo(span=LineSpan(start=chunk.start, end=chunk.end))
        for no, line in chunk.numbered():
            if m := _VERSION.match(line):
                info.version = Loc(value=m.group("v"), line=no)
                info.version_tuple = (
                    int(m.group("major")),
                    int(m.group("minor")),
                    int(m.group("patch")),
                )
            elif m := _PARAMS.match(line):
                info.parameters_raw = m.group("rest")
                info.parameters = Loc(value=parse_parameters(m.group("rest")), line=no)
            elif m := _SHARED_TREE.match(line):
                info.num_shared_tree_workers = Loc(value=int(m.group("n")), line=no)
            elif m := _WORKERS.match(line):
                info.num_workers = Loc(value=int(m.group("n")), line=no)
            else:
                info.other_lines.append(Loc(value=line, line=no))
        return info

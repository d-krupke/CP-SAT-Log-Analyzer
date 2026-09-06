"""Parser for ``Initial|Presolved optimization|satisfaction model`` blocks."""

from __future__ import annotations

import re

from ..schema.base import LineSpan, Loc
from ..schema.model import ConstraintLine, DomainLine, ModelDescription
from ..splitter import Chunk
from ..text import NUMBER_TOKEN, parse_int
from .base import BlockParser
from .domain import parse_domain

_HEADER = re.compile(
    r"^(?P<stage>Initial|Presolved) (?P<type>\w+) model '(?P<name>.*?)':?\s*"
    r"(?:\(model_fingerprint: (?P<fp>0x[0-9a-fA-F]+)\))?\s*$"
)
_VARIABLES = re.compile(rf"^#Variables:\s*(?P<n>{NUMBER_TOKEN})\s*(?P<rest>.*)$")
_BOOLS = re.compile(rf"#bools:\s*(?P<n>{NUMBER_TOKEN})")
_INTS = re.compile(rf"#ints:\s*(?P<n>{NUMBER_TOKEN})")
_PRIMARY = re.compile(rf"\((?P<n>{NUMBER_TOKEN}) primary variables\)")
_DOMAIN = re.compile(rf"^\s*-\s*(?P<n>{NUMBER_TOKEN})\s+(?P<desc>.+)$")
_CONSTRAINT = re.compile(rf"^#(?P<name>k\w+):\s*(?P<n>{NUMBER_TOKEN})\s*(?P<rest>.*)$")
_DETAIL = re.compile(rf"\(#(?P<key>\w+):\s*(?P<n>{NUMBER_TOKEN})\)")
_STRATEGY = re.compile(r"^Search strategy:")


class ModelParser(BlockParser):
    kind = "model"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return bool(_HEADER.match(chunk.first))

    @classmethod
    def parse(cls, chunk: Chunk) -> ModelDescription:
        header = _HEADER.match(chunk.first)
        assert header is not None
        model = ModelDescription(
            span=LineSpan(start=chunk.start, end=chunk.end),
            stage="initial" if header.group("stage") == "Initial" else "presolved",
            problem_type=header.group("type"),
            name=header.group("name"),
            fingerprint=header.group("fp"),
        )
        model.kind = f"{model.stage}_model"
        for no, line in chunk.numbered()[1:]:
            if m := _VARIABLES.match(line):
                model.num_variables = _loc_int(m.group("n"), no)
                rest = m.group("rest")
                if b := _BOOLS.search(rest):
                    model.num_bools_in_objective = _loc_int(b.group("n"), no)
                if i := _INTS.search(rest):
                    model.num_ints_in_objective = _loc_int(i.group("n"), no)
                if p := _PRIMARY.search(rest):
                    model.num_primary_variables = _loc_int(p.group("n"), no)
            elif m := _CONSTRAINT.match(line):
                details = {
                    d.group("key"): parse_int(d.group("n")) or 0
                    for d in _DETAIL.finditer(m.group("rest"))
                }
                model.constraints.append(
                    ConstraintLine(
                        line=no,
                        name=m.group("name"),
                        count=parse_int(m.group("n")) or 0,
                        details=details,
                    )
                )
            elif m := _DOMAIN.match(line):
                desc = m.group("desc").strip()
                model.domains.append(
                    DomainLine(
                        line=no,
                        count=parse_int(m.group("n")) or 0,
                        description=desc,
                        **parse_domain(desc),
                    )
                )
            elif _STRATEGY.match(line):
                model.search_strategies.append(Loc(value=line, line=no))
            else:
                model.other_lines.append(Loc(value=line, line=no))
        return model


def _loc_int(token: str, line: int) -> Loc[int] | None:
    value = parse_int(token)
    return None if value is None else Loc(value=value, line=line)

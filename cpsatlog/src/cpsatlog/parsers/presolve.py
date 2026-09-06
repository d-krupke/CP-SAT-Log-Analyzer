"""Parsers for the presolve log and the presolve summary.

Version traps handled here:
* >= 9.8: ``  3.26e-04s  0.00e+00d  [Name] details`` (wall time, deterministic time)
* <= 9.7: ``[Name] details time=1.2e-03s`` (only wall time, at the end)
* ``[Symmetry]`` / ``[SAT presolve]`` / ``[Probing]`` lines are multi-line reports
  rather than timed steps and are kept verbatim.
* Progress lines (``#Bound ... initial_domain``) may appear inside the block
  after ``Preloading model.``; they are left to the search-event scanner.
"""

from __future__ import annotations

import re

from ..schema.base import LineSpan, Loc
from ..schema.presolve import PresolveLog, PresolveRule, PresolveStep, PresolveSummary
from ..splitter import Chunk
from ..text import NUMBER_TOKEN, parse_float, parse_int, parse_number
from .base import BlockParser

_START = re.compile(r"^Starting presolve at (?P<t>[\d.]+)s")
_STEP_NEW = re.compile(
    r"^\s*(?P<t>[\d.eE+-]+)s\s+(?P<d>[\d.eE+-]+)d\s+\[(?P<name>[^\]]+)\]\s*(?P<rest>.*)$"
)
_STEP_OLD = re.compile(
    r"^\[(?P<name>[A-Za-z][\w ]*)\]\s*(?P<rest>.*?)(?:\s+time=(?P<t>[\d.eE+-]+)s)?\s*$"
)
_STAT = re.compile(rf"#?(?P<key>[\w/]+)=(?P<val>{NUMBER_TOKEN}(?:/{NUMBER_TOKEN})?|\S+)")
_PROGRESS = re.compile(r"^#\S+\s+[\d.]+s\b")
_VERBATIM_PREFIXES = ("[Symmetry]", "[SAT presolve]", "[Probing]", "[Cover]", "[Dual]")
_PRELOADING = re.compile(r"^Preloading model\.?$")

_SUMMARY = re.compile(r"^Presolve summary:")
_AFFINE = re.compile(rf"^\s*-\s*(?P<n>{NUMBER_TOKEN}) affine relations were detected\.")
_RULE = re.compile(rf"^\s*-\s*rule '(?P<rule>.*)' was applied (?P<n>{NUMBER_TOKEN}) times?\.")
_CLOSED = re.compile(r"^Problem closed by presolve\.")


class PresolveParser(BlockParser):
    kind = "presolve"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        first = chunk.first
        return bool(
            _START.match(first)
            or _STEP_NEW.match(first)
            or first.startswith(_VERBATIM_PREFIXES)
            or (_STEP_OLD.match(first) and not first.startswith("[skipped"))
            or _PRELOADING.match(first)
        )

    @classmethod
    def parse(cls, chunk: Chunk) -> PresolveLog:
        span = LineSpan(start=chunk.start, end=chunk.end)
        log = PresolveLog(span=span, spans=[span])
        for no, line in chunk.numbered():
            if m := _START.match(line):
                log.start_time = Loc(value=float(m.group("t")), line=no)
            elif m := _STEP_NEW.match(line):
                log.steps.append(
                    _step(no, m.group("name"), m.group("rest"), m.group("t"), m.group("d"))
                )
            elif line.startswith("[Symmetry]"):
                log.symmetry_lines.append(Loc(value=line, line=no))
            elif line.startswith("[SAT presolve]"):
                log.sat_presolve_lines.append(Loc(value=line, line=no))
            elif _PROGRESS.match(line):
                continue  # handled by the search-event scanner
            elif (m := _STEP_OLD.match(line)) and not line.startswith("[Probing]  -"):
                log.steps.append(_step(no, m.group("name"), m.group("rest"), m.group("t"), None))
            else:
                log.messages.append(Loc(value=line, line=no))
        return log


def _step(line: int, name: str, rest: str, t: str | None, d: str | None) -> PresolveStep:
    stats: dict[str, int | float | str] = {}
    for m in _STAT.finditer(rest):
        val = m.group("val")
        num = parse_number(val)
        stats[m.group("key")] = val if num is None else num
    return PresolveStep(
        line=line,
        name=name.strip(),
        time_s=parse_float(t) if t else None,
        dtime_s=parse_float(d) if d else None,
        details=rest.strip(),
        stats=stats,
    )


class PresolveSummaryParser(BlockParser):
    kind = "presolve_summary"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return bool(_SUMMARY.match(chunk.first) or _CLOSED.match(chunk.first))

    @classmethod
    def parse(cls, chunk: Chunk) -> PresolveSummary:
        summary = PresolveSummary(span=LineSpan(start=chunk.start, end=chunk.end))
        for no, line in chunk.numbered():
            if m := _AFFINE.match(line):
                summary.affine_relations = Loc(value=parse_int(m.group("n")) or 0, line=no)
            elif m := _RULE.match(line):
                summary.rules.append(
                    PresolveRule(line=no, rule=m.group("rule"), count=parse_int(m.group("n")) or 0)
                )
            elif _CLOSED.match(line):
                summary.closed_by_presolve = Loc(value=True, line=no)
            elif _SUMMARY.match(line):
                continue
            else:
                summary.other_lines.append(Loc(value=line, line=no))
        return summary

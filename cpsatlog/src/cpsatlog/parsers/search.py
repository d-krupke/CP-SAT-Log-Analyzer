"""Parser for the search block: start line, subsolver portfolio, progress events."""

from __future__ import annotations

import re

from ..schema.base import LineSpan, Loc
from ..schema.search import (
    SearchEvent,
    SearchProgress,
    SearchStart,
    SubsolverCategory,
    SubsolverEntry,
    SubsolverGroup,
)
from ..splitter import Chunk
from .base import BlockParser
from .events import parse_event

_START = re.compile(
    r"^Starting (?P<det>deterministic )?(?P<seq>sequential )?[sS]earch at (?P<t>[\d.]+)s"
    r"(?: with (?P<w>\d+) workers?)?(?: and batch size of (?P<b>\d+))?"
)
_GROUP = re.compile(
    r"^(?:(?P<n>\d+) )?(?P<label>[A-Za-z][A-Za-z ]*?subsolvers?)(?:\(s\))?:\s*\[(?P<list>.*)\]\s*$"
)
_ENTRY = re.compile(r"^(?P<name>.+?)(?:\((?P<count>\d+)\))?$")
_EVENT_LINE = re.compile(r"^#\S+\s+[\d.]+s")

_CATEGORY_BY_WORD: list[tuple[str, SubsolverCategory]] = [
    ("full", "full"),
    ("first solution", "first_solution"),
    ("interleaved", "interleaved"),
    ("incomplete", "interleaved"),
    ("helper", "helper"),
    ("ignored", "ignored"),
]


def categorize(label: str) -> SubsolverCategory:
    low = label.lower()
    for word, category in _CATEGORY_BY_WORD:
        if word in low:
            return category
    return "unknown"


class SearchParser(BlockParser):
    kind = "search"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        first = chunk.first
        return bool(_START.match(first) or _GROUP.match(first) or _EVENT_LINE.match(first))

    @classmethod
    def parse(cls, chunk: Chunk) -> SearchProgress:
        span = LineSpan(start=chunk.start, end=chunk.end)
        search = SearchProgress(span=span, spans=[span])
        other: list[Loc[str]] = []
        for no, line in chunk.numbered():
            if m := _START.match(line):
                search.start = SearchStart(
                    line=no,
                    time=float(m.group("t")),
                    num_workers=int(m.group("w")) if m.group("w") else None,
                    deterministic=bool(m.group("det")),
                    batch_size=int(m.group("b")) if m.group("b") else None,
                    sequential=bool(m.group("seq")),
                )
            elif m := _GROUP.match(line):
                search.subsolvers.append(_group(no, m))
            elif event := parse_event(line, no):
                search.events.append(event)
            else:
                other.append(Loc(value=line, line=no))
        if other:
            search.events.extend(_other_events(other))
        return search


def _group(line: int, m: re.Match[str]) -> SubsolverGroup:
    entries: list[SubsolverEntry] = []
    for raw in m.group("list").split(","):
        raw = raw.strip()
        if not raw:
            continue
        e = _ENTRY.match(raw)
        assert e is not None
        entries.append(SubsolverEntry(name=e.group("name"), count=int(e.group("count") or 1)))
    label = m.group("label")
    return SubsolverGroup(
        line=line,
        category=categorize(label),
        label=label,
        count=int(m.group("n")) if m.group("n") else len(entries),
        subsolvers=entries,
    )


def _other_events(lines: list[Loc[str]]) -> list[SearchEvent]:
    """Keep unrecognized lines inside the search block as 'other' events (time 0)."""
    return [
        SearchEvent(line=loc.line, kind="other", label="", time=0.0, message=loc.value)
        for loc in lines
    ]

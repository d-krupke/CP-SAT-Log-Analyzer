"""Parsers for the end-of-solve statistic tables.

``FormatTable`` (ortools/sat/util.cc) prints a header line ``<title>  <col>  <col>``
and one line per row ``'<name>':  <cell>  <cell>`` with at least two spaces
between cells, so splitting on runs of two or more spaces is exact. Row cells
are mapped to columns left to right; rows may have fewer cells than columns
(e.g. the ``'pump'`` repository row). Rows are sorted by name and names may
repeat (one row per worker of the same subsolver).

Known table titles are mapped to stable ``table_id``s in ``TABLE_IDS``; add a
new entry when OR-Tools introduces a table. Unknown tables are still parsed
generically (``table_id`` derived from the title).

Two variants need subclasses:
* ``TaskTimingParser`` – bracketed min/max ranges and two column groups.
* ``KeyValueListParser`` – OR-Tools <= 9.3 printed ``Solutions found per
  subsolver:`` lists instead of tables; they become one-column tables.
"""

from __future__ import annotations

import re

from ..schema.base import LineSpan
from ..schema.tables import Cell, Table, TableRow, TaskTimingRow, TaskTimingTable, TimingStats
from ..splitter import Chunk
from ..text import parse_duration, parse_number, split_columns, strip_row_name
from .base import BlockParser

TABLE_IDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^Task timing$"), "task_timing"),
    (re.compile(r"^Search stats$"), "search_stats"),
    (re.compile(r"^SAT formula$"), "sat_formula"),
    (re.compile(r"^SAT stats$"), "sat_stats"),
    (re.compile(r"^Vivification$"), "vivification"),
    (re.compile(r"^Clause deletion$"), "clause_deletion"),
    (re.compile(r"^Lp stats$"), "lp_stats"),
    (re.compile(r"^Lp dimension$"), "lp_dimension"),
    (re.compile(r"^Lp debug$"), "lp_debug"),
    (re.compile(r"^Lp pool$"), "lp_pool"),
    (re.compile(r"^Lp Cut$"), "lp_cut"),
    (re.compile(r"^LNS stats$"), "lns_stats"),
    (re.compile(r"^LS stats$"), "ls_stats"),
    (re.compile(r"^Solutions(?: \(\d+\))?$"), "solutions"),
    (re.compile(r"^Objective bounds$"), "objective_bounds"),
    (re.compile(r"^Solution repositories$"), "solution_repositories"),
    (re.compile(r"^Improving bounds shared$"), "improving_bounds_shared"),
    (re.compile(r"^Clauses shared$"), "clauses_shared"),
    (re.compile(r"^Linear2 shared$"), "linear2_shared"),
    # OR-Tools <= 9.3 key/value lists
    (re.compile(r"^Solutions found per subsolver$"), "solutions"),
    (re.compile(r"^Objective bounds found per subsolver$"), "objective_bounds"),
    (re.compile(r"^Improving variable bounds shared per subsolver$"), "improving_bounds_shared"),
]

_ROW = re.compile(r"^\s*(?P<name>'[^']*':|[A-Za-z0-9_][^\s:]*:)\s*(?P<rest>.*)$")
_TITLE_COUNT = re.compile(r"^(?P<title>.*?)\s*\((?P<n>\d+)\)$")
_LIST_HEADER = re.compile(r"^[A-Z][A-Za-z ]+:$")


def table_id_for(title: str) -> str | None:
    for pattern, table_id in TABLE_IDS:
        if pattern.match(title):
            return table_id
    return None


def _split_header(line: str) -> tuple[str, list[str]]:
    parts = split_columns(line)
    if not parts:
        return "", []
    return parts[0].strip(), [p.strip() for p in parts[1:]]


def _cell_value(text: str) -> Cell:
    text = text.strip()
    if text in {"", "-"}:
        return None
    number = parse_number(text)
    return text if number is None else number


class TableParser(BlockParser):
    kind = "table"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        title, columns = _split_header(chunk.first)
        if not title or chunk.first.startswith(("#", " ", "\t")):
            return False
        if table_id_for(title.rstrip(":")) in {None, "task_timing"}:
            # unknown title: accept only if it looks like a table (quoted row names)
            if table_id_for(title) == "task_timing":
                return False
            return (
                len(chunk.lines) > 1
                and bool(re.match(r"^\s*'[^']*':\s", chunk.lines[1]))
                and bool(columns)
            )
        return not chunk.first.endswith(":")

    @classmethod
    def parse(cls, chunk: Chunk) -> Table:
        raw_title, columns = _split_header(chunk.first)
        title, count = raw_title, None
        if m := _TITLE_COUNT.match(raw_title):
            title, count = m.group("title"), int(m.group("n"))
        table_id = table_id_for(raw_title) or table_id_for(title) or _slug(title)
        table = Table(
            span=LineSpan(start=chunk.start, end=chunk.end),
            table_id=table_id,
            title=raw_title,
            header_line=chunk.start,
            columns=columns,
            count=count,
        )
        for no, line in chunk.numbered()[1:]:
            m = _ROW.match(line)
            if not m:
                continue
            cells = split_columns(m.group("rest"))
            values: dict[str, Cell] = {}
            for col, cell in zip(columns, cells, strict=False):
                values[col] = _cell_value(cell)
            table.rows.append(
                TableRow(name=strip_row_name(m.group("name")), line=no, cells=cells, values=values)
            )
        return table


class TaskTimingParser(BlockParser):
    kind = "task_timing"
    _ROW = re.compile(
        r"^\s*'(?P<name>[^']*)':\s+(?P<n1>\d+)\s+\[\s*(?P<min1>\S+),\s*(?P<max1>\S+)\]\s+"
        r"(?P<avg1>\S+)\s+(?P<dev1>\S+)\s+(?P<tot1>\S+)"
        r"(?:\s+(?P<n2>\d+)\s+\[\s*(?P<min2>\S+),\s*(?P<max2>\S+)\]\s+"
        r"(?P<avg2>\S+)\s+(?P<dev2>\S+)\s+(?P<tot2>\S+))?\s*$"
    )

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return chunk.first.startswith("Task timing")

    @classmethod
    def parse(cls, chunk: Chunk) -> TaskTimingTable:
        table = TaskTimingTable(
            span=LineSpan(start=chunk.start, end=chunk.end), header_line=chunk.start
        )
        for no, line in chunk.numbered()[1:]:
            m = cls._ROW.match(line)
            if not m:
                continue
            wall = _timing(m, "1")
            det = _timing(m, "2") if m.group("n2") else None
            if wall is None:
                continue
            table.rows.append(
                TaskTimingRow(name=m.group("name"), line=no, wall=wall, deterministic=det)
            )
        return table


def _timing(m: re.Match[str], suffix: str) -> TimingStats | None:
    values = [
        parse_duration(m.group(f"{key}{suffix}")) for key in ("min", "max", "avg", "dev", "tot")
    ]
    if any(v is None for v in values):
        return None
    mn, mx, avg, dev, tot = (float(v) for v in values if v is not None)
    return TimingStats(n=int(m.group(f"n{suffix}")), min=mn, max=mx, avg=avg, dev=dev, total=tot)


class KeyValueListParser(BlockParser):
    """``Solutions found per subsolver:`` + ``  'name': 3`` lines (OR-Tools <= 9.3)."""

    kind = "table"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        if not _LIST_HEADER.match(chunk.first) or len(chunk.lines) < 2:
            return False
        return table_id_for(chunk.first[:-1]) is not None

    @classmethod
    def parse(cls, chunk: Chunk) -> Table:
        title = chunk.first[:-1]
        table = Table(
            span=LineSpan(start=chunk.start, end=chunk.end),
            table_id=table_id_for(title) or _slug(title),
            title=title,
            header_line=chunk.start,
            columns=["Num"],
        )
        for no, line in chunk.numbered()[1:]:
            m = _ROW.match(line)
            if not m:
                continue
            cell = m.group("rest").strip()
            table.rows.append(
                TableRow(
                    name=strip_row_name(m.group("name")),
                    line=no,
                    cells=[cell],
                    values={"Num": _cell_value(cell)},
                )
            )
        return table


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")

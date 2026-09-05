"""Schema for the statistic tables CP-SAT prints at the end of a solve.

All tables (``Search stats``, ``Lp stats``, ``Solutions (N)``, ...) share one
layout produced by OR-Tools' ``FormatTable``: a header row with the table name
and right-aligned column names, followed by one row per subsolver whose first
cell is the quoted row name. ``Table`` models that generically; ``table_id`` is
a stable identifier (``search_stats``, ``lp_pool``, ...) that survives column
renames between OR-Tools versions, so consumers should key on it rather than on
the printed title.

``TaskTimingTable`` is the one table with a different shape (two groups of
``n [min, max] avg dev total`` for wall time and deterministic time), so it gets
its own typed model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Block

Cell = int | float | str | None


class TableRow(BaseModel):
    name: str
    line: int = Field(ge=1)
    cells: list[str] = Field(default_factory=list, description="Raw cell texts")
    values: dict[str, Cell] = Field(
        default_factory=dict, description="Column name -> parsed cell (numbers converted)"
    )


class Table(Block):
    kind: str = "table"
    table_id: str
    title: str
    header_line: int = Field(ge=1)
    columns: list[str] = Field(default_factory=list)
    rows: list[TableRow] = Field(default_factory=list)
    count: int | None = Field(
        default=None, description="Number in the title, e.g. the N of 'Solutions (N)'"
    )

    def row(self, name: str) -> TableRow | None:
        for r in self.rows:
            if r.name == name:
                return r
        return None

    def column(self, column: str) -> dict[str, Cell]:
        return {r.name: r.values.get(column) for r in self.rows}


class TimingStats(BaseModel):
    n: int
    min: float
    max: float
    avg: float
    dev: float
    total: float


class TaskTimingRow(BaseModel):
    name: str
    line: int = Field(ge=1)
    wall: TimingStats
    deterministic: TimingStats | None = None


class TaskTimingTable(Block):
    kind: str = "task_timing"
    table_id: str = "task_timing"
    title: str = "Task timing"
    header_line: int = Field(ge=1)
    rows: list[TaskTimingRow] = Field(default_factory=list)

    def row(self, name: str) -> TaskTimingRow | None:
        for r in self.rows:
            if r.name == name:
                return r
        return None


class FinalStats(BaseModel):
    """All end-of-solve tables, keyed by their stable id. Missing tables are ``None``."""

    task_timing: TaskTimingTable | None = None
    search_stats: Table | None = None
    sat_formula: Table | None = None
    sat_stats: Table | None = None
    vivification: Table | None = None
    clause_deletion: Table | None = None
    lp_stats: Table | None = None
    lp_dimension: Table | None = None
    lp_debug: Table | None = None
    lp_pool: Table | None = None
    lp_cut: Table | None = None
    lns_stats: Table | None = None
    ls_stats: Table | None = None
    solutions: Table | None = None
    objective_bounds: Table | None = None
    solution_repositories: Table | None = None
    improving_bounds_shared: Table | None = None
    clauses_shared: Table | None = None
    linear2_shared: Table | None = None
    other: list[Table] = Field(default_factory=list, description="Tables with unknown ids")

    def all_tables(self) -> list[Table | TaskTimingTable]:
        result: list[Table | TaskTimingTable] = []
        for name in type(self).model_fields:
            if name == "other":
                continue
            value = getattr(self, name)
            if value is not None:
                result.append(value)
        result.extend(self.other)
        return result

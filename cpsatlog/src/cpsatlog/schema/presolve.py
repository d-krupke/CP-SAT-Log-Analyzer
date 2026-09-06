"""Schema for the presolve log and the presolve summary."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Block, LineSpan, Loc


class PresolveStep(BaseModel):
    """One ``  3.26e-04s  0.00e+00d  [DetectDominanceRelations] key=val`` line.

    Older versions print ``[Name] key=val time=0.1s`` instead; then ``time_s`` is
    taken from the trailing ``time=`` and ``dtime_s`` stays ``None``.
    """

    line: int
    name: str
    time_s: float | None = None
    dtime_s: float | None = None
    details: str = ""
    stats: dict[str, int | float | str] = Field(
        default_factory=dict, description="Parsed '#key=value' pairs from details"
    )


class PresolveLog(Block):
    kind: str = "presolve"
    spans: list[LineSpan] = Field(default_factory=list, description="All blocks merged here")
    start_time: Loc[float] | None = None
    steps: list[PresolveStep] = Field(default_factory=list)
    symmetry_lines: list[Loc[str]] = Field(default_factory=list)
    sat_presolve_lines: list[Loc[str]] = Field(default_factory=list)
    messages: list[Loc[str]] = Field(
        default_factory=list, description="Hints, infeasibility notices, other free text"
    )

    @property
    def total_step_time(self) -> float:
        return sum(s.time_s or 0.0 for s in self.steps)


class PresolveRule(BaseModel):
    line: int
    rule: str
    count: int


class PresolveSummary(Block):
    kind: str = "presolve_summary"
    affine_relations: Loc[int] | None = None
    rules: list[PresolveRule] = Field(default_factory=list)
    closed_by_presolve: Loc[bool] | None = Field(
        default=None, description="Set when 'Problem closed by presolve.' was printed"
    )
    other_lines: list[Loc[str]] = Field(default_factory=list)

"""Schema for the ``Initial ... model`` and ``Presolved ... model`` blocks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .base import Block, Loc


class DomainLine(BaseModel):
    """``  - 3'000 Booleans in [0,1]`` / ``  - 20 in [0,10]`` / ``- 4 constants in {0,1}``.

    ``count`` is the number of variables with this domain (for ``kind == "summary"`` the
    number of distinct domains). The structured fields come from ``parsers.domain``.
    """

    line: int
    count: int
    description: str = Field(description="Text after the count, e.g. 'Booleans in [0,1]'")
    kind: Literal["bool", "int", "constant", "summary", "other"] = "other"
    lo: int | None = Field(default=None, description="Smallest value of the domain")
    hi: int | None = Field(default=None, description="Largest value of the domain")
    size: int | None = Field(default=None, description="Number of values; None if unknown")
    intervals: int | None = Field(
        default=None, description="Number of intervals (1 = no holes); None if unknown"
    )
    truncated: bool = Field(default=False, description="The solver shortened the line with ' ... '")


class ConstraintLine(BaseModel):
    """``#kLinearN: 94 (#enforced: 18) (#terms: 1'392)``."""

    line: int
    name: str = Field(description="Constraint kind without '#', e.g. 'kLinearN'")
    count: int
    details: dict[str, int] = Field(default_factory=dict, description="e.g. {'enforced': 18}")


class ModelDescription(Block):
    kind: str = "model"
    stage: Literal["initial", "presolved"]
    problem_type: str | None = Field(default=None, description="'optimization' or 'satisfaction'")
    name: str | None = None
    fingerprint: str | None = None
    num_variables: Loc[int] | None = None
    num_bools_in_objective: Loc[int] | None = None
    num_ints_in_objective: Loc[int] | None = None
    num_primary_variables: Loc[int] | None = None
    domains: list[DomainLine] = Field(default_factory=list)
    constraints: list[ConstraintLine] = Field(default_factory=list)
    search_strategies: list[Loc[str]] = Field(default_factory=list)
    other_lines: list[Loc[str]] = Field(default_factory=list)

    @property
    def num_constraints(self) -> int:
        return sum(c.count for c in self.constraints)

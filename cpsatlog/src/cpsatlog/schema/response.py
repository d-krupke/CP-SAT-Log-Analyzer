"""Schema for the ``CpSolverResponse summary:`` block."""

from __future__ import annotations

from pydantic import Field

from .base import Block, Loc


class ResponseSummary(Block):
    kind: str = "response"
    status: Loc[str] | None = None
    objective: Loc[float] | None = Field(default=None, description="None when printed as NA")
    best_bound: Loc[float] | None = None
    integers: Loc[int] | None = None
    booleans: Loc[int] | None = None
    conflicts: Loc[int] | None = None
    branches: Loc[int] | None = None
    propagations: Loc[int] | None = None
    integer_propagations: Loc[int] | None = None
    restarts: Loc[int] | None = None
    lp_iterations: Loc[int] | None = None
    walltime: Loc[float] | None = None
    usertime: Loc[float] | None = None
    deterministic_time: Loc[float] | None = None
    gap_integral: Loc[float] | None = None
    solution_fingerprint: Loc[str] | None = None
    lrat_status: Loc[str] | None = None
    extra: dict[str, Loc[str]] = Field(default_factory=dict, description="Unknown key: value lines")

    @property
    def gap(self) -> float | None:
        """Relative gap in percent as CP-SAT defines it: |obj-bound| / max(1,|obj|)."""
        if self.objective is None or self.best_bound is None:
            return None
        obj = self.objective.value
        return 100.0 * abs(obj - self.best_bound.value) / max(1.0, abs(obj))

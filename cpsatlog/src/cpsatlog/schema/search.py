"""Schema for the search phase: start line, subsolver portfolio and progress events.

Progress lines (``#1``, ``#Bound``, ``#Model``, ``#Done``) can appear in several
blank-line separated blocks and even inside the presolve block (``Preloading
model.`` followed by ``#Bound ... initial_domain``). The parser therefore scans
the whole log for them and collects everything into one ``SearchProgress`` whose
``spans`` lists every contributing block.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .base import Block, LineSpan

SubsolverCategory = Literal["full", "first_solution", "interleaved", "helper", "ignored", "unknown"]
EventKind = Literal["solution", "bound", "model", "done", "other"]
ObjectiveSense = Literal["minimize", "maximize"]


class SearchStart(BaseModel):
    line: int
    time: float
    num_workers: int | None = None
    deterministic: bool = False
    batch_size: int | None = None
    sequential: bool = False


class SubsolverEntry(BaseModel):
    name: str
    count: int = 1


class SubsolverGroup(BaseModel):
    line: int
    category: SubsolverCategory
    label: str = Field(description="Wording used by this version, e.g. 'incomplete subsolvers'")
    count: int | None = None
    subsolvers: list[SubsolverEntry] = Field(default_factory=list)


class SearchEvent(BaseModel):
    line: int
    kind: EventKind
    label: str = Field(description="'#1', '#Bound', '#Model', '#Done', ...")
    time: float
    solution_index: int | None = None
    objective: float | None = Field(default=None, description="best: value (None for 'inf')")
    objective_infinite: str | None = Field(
        default=None,
        description="'inf' (minimization) or '-inf' (maximization) before any solution",
    )
    next_lb: float | None = None
    next_ub: float | None = None
    subsolver: str | None = None
    message: str = ""
    tags: list[str] = Field(default_factory=list, description="e.g. ['hint', 'presolve']")
    skipped_logs: int | None = None
    model_vars: int | None = None
    model_vars_total: int | None = None
    model_constraints: int | None = None
    model_constraints_total: int | None = None
    model_components: list[int] = Field(
        default_factory=list,
        description="'compo:' on a #Model line: sizes of the connected components, descending",
    )
    model_components_truncated: bool = Field(
        default=False, description="True when CP-SAT printed only the 10 largest components"
    )

    def bound(self, sense: ObjectiveSense | None) -> float | None:
        """The proven bound implied by ``next:[lb,ub]`` for the given objective sense."""
        if sense == "maximize":
            return self.next_ub
        if sense == "minimize":
            return self.next_lb
        return None


class SearchProgress(Block):
    kind: str = "search"
    spans: list[LineSpan] = Field(default_factory=list)
    start: SearchStart | None = None
    subsolvers: list[SubsolverGroup] = Field(default_factory=list)
    events: list[SearchEvent] = Field(default_factory=list)
    objective_sense: ObjectiveSense | None = Field(
        default=None, description="Derived from best/next values; None for satisfaction"
    )

    def events_of_kind(self, kind: EventKind) -> list[SearchEvent]:
        return [e for e in self.events if e.kind == kind]

    def subsolver_names(self, category: SubsolverCategory) -> list[str]:
        return [s.name for g in self.subsolvers if g.category == category for s in g.subsolvers]

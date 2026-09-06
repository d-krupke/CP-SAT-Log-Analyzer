"""What became of the solution hint: the ``HintReport`` shown in its own card.

Created 2026-09. The parser collects the hint-related lines verbatim
(``CpSatLog.hints``); this module decides what they mean, which is not obvious:

* CP-SAT checks the hint twice, once on the model as given and once on the
  presolved model, so a log can carry two verdicts. The later one decides.
* When the post-presolve hint is complete and feasible, CP-SAT logs *nothing*
  and instead pushes it into the solution pool under the worker name
  ``complete_hint``. That solution event is the proof that the hint was used.
* ``The solution hint is complete and is feasible.`` also appears when no hint
  was given at all: the check short-circuits on a model without non-fixed
  variables, which happens whenever presolve solves the model outright (11 logs
  of the benchmark corpus, e.g. every sudoku). Such a line is *vacuous* and must
  not be reported as a hint.

Change this when a new OR-Tools version adds a hint line: add the wording to
``cpsatlog.parsers.hints`` first, then map its kind here.
"""

from __future__ import annotations

from typing import Literal

from cpsatlog import CpSatLog
from cpsatlog.schema import HintNote
from pydantic import BaseModel, Field

HintStatus = Literal[
    "none",
    "vacuous",
    "accepted",
    "infeasible",
    "incomplete",
    "outside_domain",
    "breaks_assumptions",
    "ignored",
    "debug_only",
    "other",
]

# The verdicts of a hint check, in the wording-independent form used above.
_VERDICTS: dict[str, HintStatus] = {
    "hint_complete_feasible": "accepted",
    "hint_complete_infeasible": "infeasible",
    "hint_incomplete": "incomplete",
    "hint_outside_domain": "outside_domain",
    "hint_breaks_assumptions": "breaks_assumptions",
    "hint_other": "other",
}

COMPLETE_HINT = "complete_hint"


class HintReport(BaseModel):
    """Everything the log says about the solution hint (empty when it says nothing)."""

    provided: bool = Field(description="Is there evidence that a hint was actually given?")
    status: HintStatus
    notes: list[HintNote] = Field(default_factory=list, description="The hint lines, in log order")
    used_as_first_solution: bool = False
    first_solution_line: int | None = None
    objective: float | None = Field(default=None, description="Objective value of a feasible hint")
    hinted: int | None = Field(default=None, description="Non-fixed variables that were hinted")
    active: int | None = Field(default=None, description="Non-fixed variables of the model")
    fixed_variables: int | None = Field(
        default=None, description="Variables hard-fixed to their hinted value by presolve"
    )
    lines: list[int] = Field(default_factory=list, description="Evidence lines for the UI")

    @property
    def has_evidence(self) -> bool:
        """Is there anything to show? (Vacuous lines count: they need explaining.)"""
        return bool(self.notes) or self.used_as_first_solution


def build_hint_report(log: CpSatLog) -> HintReport:
    notes = sorted(log.hints, key=lambda n: n.line)
    used_line, used_objective = _complete_hint(log)
    verdicts = [n for n in notes if n.kind in _VERDICTS and not _is_vacuous(log, n)]
    status = _status(notes, verdicts, used_line)
    fixing = _last(notes, "hint_fixed_variables")
    report = HintReport(
        provided=status not in ("none", "vacuous"),
        status=status,
        notes=notes,
        used_as_first_solution=used_line is not None,
        first_solution_line=used_line,
        fixed_variables=int(fixing.numbers["variables"]) if fixing else None,
        lines=[n.line for n in notes] + ([used_line] if used_line is not None else []),
    )
    feasible = _last(verdicts, "hint_complete_feasible")
    if feasible is not None:
        report.objective = feasible.numbers.get("objective")
    # Only the pre-presolve line states the objective, and only for an optimization
    # model; the `complete_hint` solution carries it in every other case.
    if report.objective is None:
        report.objective = used_objective
    incomplete = _last(verdicts, "hint_incomplete")
    if incomplete is not None:
        report.hinted = int(incomplete.numbers["hinted"])
        report.active = int(incomplete.numbers["active"])
    return report


def _status(notes: list[HintNote], verdicts: list[HintNote], used_line: int | None) -> HintStatus:
    """The fate of the hint: an explicit rejection wins, otherwise the last verdict."""
    kinds = {n.kind for n in notes}
    if "hint_ignored" in kinds:
        return "ignored"
    if "hint_debug_only" in kinds:
        return "debug_only"
    if verdicts:
        return _VERDICTS[verdicts[-1].kind]
    if used_line is not None or "hint_fixed_variables" in kinds:
        return "accepted"
    return "vacuous" if notes else "none"


def _last(notes: list[HintNote], kind: str) -> HintNote | None:
    return next((n for n in reversed(notes) if n.kind == kind), None)


def _is_vacuous(log: CpSatLog, note: HintNote) -> bool:
    """Did this check run on a model without non-fixed variables (so it proves nothing)?

    ``SolutionHintIsCompleteAndFeasible`` returns early only when there is no hint *and* the
    model has variables. With ``#Variables: 0`` it therefore reports a complete, feasible hint
    for a model that has none - which is exactly what a log looks like when presolve solved
    the model on its own.
    """
    if note.kind != "hint_complete_feasible":
        return False
    model = log.presolved_model if _after_presolve(log, note.line) else log.initial_model
    return model is not None and model.num_variables is not None and model.num_variables.value == 0


def _after_presolve(log: CpSatLog, line: int) -> bool:
    model = log.presolved_model
    return model is not None and line >= model.span.start


def _complete_hint(log: CpSatLog) -> tuple[int | None, float | None]:
    """Line and objective of the solution CP-SAT took straight from the hint, if there is one.

    The hint enters the pool under the worker name ``complete_hint``; it shows up as a ``#1``
    event (with its objective) and in the final ``Solutions`` table (without one).
    """
    if log.search:
        for event in log.search.events:
            if event.kind == "solution" and event.subsolver == COMPLETE_HINT:
                return event.line, event.objective
    table = log.stats.solutions
    if table is not None:
        row = table.row(COMPLETE_HINT)
        if row is not None:
            return row.line, None
    return None, None

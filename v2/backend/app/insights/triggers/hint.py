"""What became of the solution hint - including the case where there was none.

The hint is the caller's own input, so the log is the only place where they can
learn what CP-SAT made of it, and that verdict is one line in the middle of the
presolve output. ``app/hints.py`` turns those lines into a ``HintReport``; the
triggers here only pick the matching status apart.
"""

from __future__ import annotations

from ..base import Context, Insight, Trigger

MAX_EVIDENCE_LINES = 3


class HintUsedAsFirstSolution(Trigger):
    order = 60
    level = "good"
    title = "Hint used as the first solution"

    def check(self, ctx: Context) -> Insight | None:
        hint = ctx.hint
        if hint.status != "accepted" or not hint.used_as_first_solution:
            return None
        return self.fire(
            """
            The solution hint was complete and feasible, and CP-SAT put it straight into the
            solution pool as solution `#1` under the worker name `complete_hint`. Every worker
            started from that incumbent, so the objective curve begins at your value instead of
            at the first solution the portfolio could find on its own.
            """,
            hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintAcceptedButUnused(Trigger):
    """Feasible before presolve, yet no `complete_hint` solution: the second check is silent."""

    order = 60
    level = "good"
    title = "Hint complete and feasible"

    def check(self, ctx: Context) -> Insight | None:
        hint = ctx.hint
        if hint.status != "accepted" or hint.used_as_first_solution:
            return None
        return self.fire(
            """
            CP-SAT checked the hint and found it complete and feasible. Note that this line
            comes from the check on the model *as given*; the solver checks again after presolve
            and only then adds the hint to the solution pool (as `complete_hint`). No such
            solution appears in this log, so either presolve changed the model in a way that
            broke the hint, or the run stopped before the search started.
            """,
            hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintInfeasible(Trigger):
    order = 60
    level = "warn"
    title = "Hint is infeasible"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.hint.status != "infeasible":
            return None
        return self.fire(
            """
            The hint assigned every variable but the assignment violates a constraint, so
            CP-SAT could not use it as a solution. It spends `hint_conflict_limit` conflicts
            trying to repair it (`repair_hint`) and then searches normally. An infeasible hint
            is usually a mismatch between the model you hinted and the model you solved - e.g.
            values from an earlier run whose constraints have since changed. Set
            `debug_crash_on_bad_hint` while developing to find out which constraint it breaks.
            """,
            ctx.hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintIncomplete(Trigger):
    order = 60
    level = "info"
    title = "Hint is incomplete"

    def check(self, ctx: Context) -> Insight | None:
        hint = ctx.hint
        if hint.status != "incomplete" or hint.hinted is None or hint.active is None:
            return None
        return self.fire(
            f"""
            Only {hint.hinted} of the {hint.active} non-fixed variables were hinted, so the hint
            cannot be used as a solution directly: CP-SAT follows it as a branching preference
            and searches for values for the rest. That is a perfectly good way to use hints, but
            it does not give you a starting incumbent - if you want one, hint every variable
            (typically by taking a full solution from an earlier run) and check for the
            `complete_hint` solution in the search log.
            """,
            hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintOutsideDomain(Trigger):
    order = 60
    level = "warn"
    title = "Hint outside the variable domains"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.hint.status != "outside_domain":
            return None
        return self.fire(
            """
            The hint assigns a value that the variable's own domain does not contain, so it is
            ignored as a solution. This is nearly always a stale hint: the domains were
            tightened (or the variables rebuilt) after the values were produced.
            """,
            ctx.hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintBreaksAssumptions(Trigger):
    order = 60
    level = "warn"
    title = "Hint breaks the assumptions"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.hint.status != "breaks_assumptions":
            return None
        return self.fire(
            """
            The hint is a feasible solution of the model but contradicts one of the assumption
            literals of this solve, so it cannot be used. Drop the assumptions or hint a
            solution that satisfies them.
            """,
            ctx.hint.lines[:MAX_EVIDENCE_LINES],
        )


class HintIgnored(Trigger):
    order = 60
    level = "info"
    title = "Hint ignored"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.hint.status != "ignored":
            return None
        return self.fire(
            """
            The hint was dropped before the solve because the run set `cp_model_ignore_hints`.
            Nothing in this log reflects your hinted values.
            """,
            ctx.hint.lines[:MAX_EVIDENCE_LINES],
        )


class VacuousHintLine(Trigger):
    """The trap: the line appears for 11 of the 295 corpus logs that were given no hint."""

    order = 60
    level = "info"
    title = "The hint line here means nothing"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.hint.status != "vacuous":
            return None
        return self.fire(
            """
            `The solution hint is complete and is feasible.` also appears when **no** hint was
            given: the check short-circuits on a model that has no non-fixed variables left,
            which is what happens when presolve solves the model outright. Do not read this
            line as "my hint was accepted".
            """,
            ctx.hint.lines[:1],
        )

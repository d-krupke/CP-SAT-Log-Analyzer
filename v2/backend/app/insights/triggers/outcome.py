"""How the run ended: the box that answers "did this solve work?".

One trigger per status, so each one says only what its own status implies.
"""

from __future__ import annotations

from ..base import Context, Insight, Trigger


class SolvedByPresolve(Trigger):
    order = 20
    level = "good"
    title = "Solved by presolve"

    def check(self, ctx: Context) -> Insight | None:
        summary = ctx.log.presolve_summary
        if summary is None or not summary.closed_by_presolve:
            return None
        return self.fire(
            """
            Presolve alone settled the model; no search was needed. The search statistics are
            therefore empty.
            """,
            [summary.closed_by_presolve.line],
        )


class NotProvenOptimal(Trigger):
    """A solution without a proof: the gap is the one number that says how far off it may be."""

    order = 20
    level = "warn"
    title = "Not proven optimal"

    def check(self, ctx: Context) -> Insight | None:
        gap = ctx.response.gap if ctx.response else None
        if ctx.status != "FEASIBLE" or gap is None:
            return None
        return self.fire(
            f"""
            The solver stopped with a gap of {gap:.2f}%: the incumbent may not be optimal, or it
            is optimal and the bound could not be raised to prove it. Whether solutions or the
            bound stalled first (progress plot) tells you which of the two you are looking at.
            """,
            ctx.status_lines,
        )


class NoSolution(Trigger):
    order = 20
    level = "bad"
    title = "No solution found"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.status != "UNKNOWN":
            return None
        return self.fire(
            """
            The solver found no feasible solution within the limits, and did not prove that
            none exists.
            """,
            ctx.status_lines,
        )


class ProvenInfeasible(Trigger):
    order = 20
    level = "info"
    title = "Model proven infeasible"

    def check(self, ctx: Context) -> Insight | None:
        if ctx.status != "INFEASIBLE":
            return None
        return self.fire(
            """
            Infeasibility was proven: no assignment satisfies all constraints. The presolve log
            is the place to look - often a variable fixed to a value or a domain that presolve
            emptied points at the conflicting constraints.
            """,
            ctx.status_lines,
        )

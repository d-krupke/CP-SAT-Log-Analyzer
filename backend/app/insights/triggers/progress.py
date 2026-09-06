"""What the objective and bound curves did over time.

Both triggers only fire on a run that ended FEASIBLE, i.e. one that was still
working when the time ran out: on an OPTIMAL run the curves stop early by
definition and saying so would be noise.
"""

from __future__ import annotations

from ..base import Context, Insight, Trigger


class SolutionsStalled(Trigger):
    order = 30
    level = "info"
    title = "Solutions stalled early"
    #: Fires when the last improving solution came before this share of the wall time.
    max_share_of_walltime = 0.5

    def check(self, ctx: Context) -> Insight | None:
        wall = ctx.walltime
        if ctx.status != "FEASIBLE" or not wall or not ctx.progress.solutions:
            return None
        last = ctx.progress.solutions[-1]
        if last.time >= self.max_share_of_walltime * wall:
            return None
        return self.fire(
            f"""
            The last improving solution was found at {last.time:.1f}s of {wall:.1f}s. The
            remaining time went into (unsuccessful) proving. If the bound also stalled, the
            solution may well be optimal but hard to prove.
            """,
            [last.line],
        )


class BoundStalled(Trigger):
    order = 30
    level = "info"
    title = "Bound stalled early"
    max_share_of_walltime = 0.5

    def check(self, ctx: Context) -> Insight | None:
        wall = ctx.walltime
        if ctx.status != "FEASIBLE" or not wall or not ctx.progress.bounds:
            return None
        last = ctx.progress.bounds[-1]
        if last.time >= self.max_share_of_walltime * wall:
            return None
        return self.fire(
            f"""
            The proven bound last improved at {last.time:.1f}s of {wall:.1f}s, so most of the
            run raised it no further. A bound that moves this slowly usually comes from a weak
            relaxation - big-M formulations are the classic case.
            """,
            [last.line],
        )

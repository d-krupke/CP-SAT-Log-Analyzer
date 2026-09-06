"""The solver portfolio: what a worker count below the full portfolio costs.

Created 2026-09. This used to be a two-sentence hint printed inside the Workers
tile, which is a box the size of a number: it had room for the threshold but not
for the difference between "one worker" and "a reduced portfolio", and it could
not point at the portfolio listing that proves either. A box can.
"""

from __future__ import annotations

from inspect import cleandoc

from cpsat_logutils.schema.search import SubsolverGroup

from ..base import Context, Insight, Trigger


def started(group: SubsolverGroup) -> str:
    """One portfolio line as the log states it, e.g. ``1 full problem subsolver: [main]``."""
    count = group.count if group.count is not None else len(group.subsolvers)
    names = ", ".join(entry.name for entry in group.subsolvers)
    return f"{count} {group.label}: [{names}]"


class PartialPortfolio(Trigger):
    """Fewer workers changes *which* strategies run, not only how fast they run.

    CP-SAT spends its worker budget on a portfolio of different strategies. Below
    the full budget it does not run the same search more slowly - it leaves whole
    categories out, and that is invisible in the progress plot: the run simply
    never tries what was dropped.
    """

    order = 40
    level = "warn"
    title = "Only part of the portfolio ran"
    #: Below this many workers CP-SAT starts dropping strategies. Same threshold as
    #: the Workers tile (``min_for_full_portfolio`` in ``knowledge/metrics.toml``);
    #: ``test_insights.py`` fails if the two ever disagree.
    min_for_full_portfolio = 8

    def check(self, ctx: Context) -> Insight | None:
        workers = ctx.num_workers
        if workers is None or workers.value >= self.min_for_full_portfolio:
            return None

        if workers.value == 1:
            prose = cleandoc("""
                CP-SAT ran with a single worker, so there was no portfolio: one search with
                your parameters, no LNS and no separate first-solution worker. Nothing
                compensates for a strategy that suits this model badly, and nothing else is
                available to raise the bound while that search runs.
            """)
        else:
            prose = cleandoc(f"""
                CP-SAT ran with {workers.value} workers, fewer than the
                {self.min_for_full_portfolio} a full portfolio uses, so it started only a
                subset of its strategies.
            """)

        search = ctx.log.search
        groups = [g for g in search.subsolvers if g.category != "helper"] if search else []
        if not groups:
            return self.fire(prose, [workers.line])
        listing = "\n".join(f"* {started(g)}" for g in groups)
        return self.fire(
            f"{prose}\n\nWhat it started:\n\n{listing}",
            [workers.line, *(g.line for g in groups)],
        )

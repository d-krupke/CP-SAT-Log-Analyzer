"""What the `Search stats` table says about the shape of the search.

Both triggers look at the worker with the most conflicts - the one that did the
combinatorial work - and at its conflicts-per-branch ratio. The two thresholds
are far apart on purpose: only the clear cases are worth a box.
"""

from __future__ import annotations

from cpsatlog import CpSatLog
from cpsatlog.schema import TableRow

from ..base import Context, Insight, Trigger


def busiest_worker(log: CpSatLog) -> tuple[TableRow, float, float] | None:
    """The row with the most conflicts, with its conflicts and branches.

    Rows whose cells are not numbers, and rows without branches (a worker that never got to
    search), are skipped rather than picked and discarded - otherwise a single such row at the
    top of the table would silence both triggers.
    """
    table = log.stats.search_stats
    if table is None:
        return None
    best: tuple[TableRow, float, float] | None = None
    for row in table.rows:
        conflicts, branches = row.values.get("Conflicts"), row.values.get("Branches")
        if not isinstance(conflicts, int | float) or not isinstance(branches, int | float):
            continue
        if branches <= 0 or (best is not None and conflicts <= best[1]):
            continue
        best = (row, float(conflicts), float(branches))
    return best


class ConflictHeavy(Trigger):
    order = 40
    level = "info"
    title = "Conflict-heavy search"
    min_ratio = 0.5

    def check(self, ctx: Context) -> Insight | None:
        found = busiest_worker(ctx.log)
        if found is None:
            return None
        row, conflicts, branches = found
        if conflicts / branches <= self.min_ratio:
            return None
        return self.fire(
            f"""
            Worker `{row.name}` hit {conflicts:,.0f} conflicts in {branches:,.0f} branches, so
            it learned a clause from most of its decisions. That is what a tightly constrained
            combinatorial core looks like from the outside.
            """,
            [row.line],
        )


class FeasibleDescent(Trigger):
    order = 40
    level = "info"
    title = "Mostly feasible descent"
    max_ratio = 0.05

    def check(self, ctx: Context) -> Insight | None:
        found = busiest_worker(ctx.log)
        if found is None:
            return None
        row, conflicts, branches = found
        if conflicts / branches >= self.max_ratio:
            return None
        return self.fire(
            f"""
            Even the busiest worker, `{row.name}`, hit only {conflicts:,.0f} conflicts in
            {branches:,.0f} branches: it rarely ran into a dead end. Finding *a* solution is
            not what this model is spending its time on.
            """,
            [row.line],
        )

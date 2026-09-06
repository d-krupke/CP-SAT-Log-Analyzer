"""Large-neighborhood search: what the `LNS stats` table shows about the sub-problems."""

from __future__ import annotations

from typing import Any

from ..base import Context, Insight, Trigger


def percent(cell: Any) -> float | None:
    """Value of a percentage cell such as ``50%``.

    The LNS stats table prints `Closed` with a percent sign, so the parser keeps it as text;
    without this the trigger silently never fired (found while mining the benchmark corpus).
    """
    if isinstance(cell, int | float):
        return float(cell)
    if isinstance(cell, str):
        try:
            return float(cell.removesuffix("%"))
        except ValueError:
            return None
    return None


class LnsClosedQuickly(Trigger):
    """Neighborhoods that are solved to completion mean the difficulty is raised adaptively."""

    order = 50
    level = "info"
    title = "LNS neighborhoods closed quickly"
    #: A neighborhood counts as "closed quickly" above this `Closed` value ...
    closed_percent = 80
    #: ... and the box needs this many such rows, and at least half of all rows.
    min_rows = 3

    def check(self, ctx: Context) -> Insight | None:
        table = ctx.log.stats.lns_stats
        if table is None:
            return None
        high = [
            row
            for row in table.rows
            if (closed := percent(row.values.get("Closed"))) is not None
            and closed > self.closed_percent
        ]
        if len(high) < max(self.min_rows, len(table.rows) // 2):
            return None
        return self.fire(
            f"""
            Most LNS neighborhoods ({len(high)} of {len(table.rows)}) were solved to
            completion; the sub-problems are easy, so the difficulty is raised adaptively.
            Consider whether the solutions came mostly from LNS (Solutions table) or from the
            exact workers.
            """,
            [row.line for row in high[:3]],
        )

"""Facts about the solver *setup* that more than one consumer needs.

Created 2026-09 when the explanation of a small worker count moved from the
Workers tile into an insight trigger: both the tile (``metrics.py``) and the
trigger have to agree on how many workers ran, and CP-SAT states that in three
different places depending on how the run was configured. One function decides,
both callers ask it.

Add a function here when a second module starts reading the same thing off the
solver header; keep it a pure read of the parsed log (no thresholds, no texts).
"""

from __future__ import annotations

from cpsatlog import CpSatLog
from cpsatlog.schema import Loc


def num_workers(log: CpSatLog) -> Loc[int] | None:
    """How many workers CP-SAT ran with, and the line that says so.

    Three sources, most explicit first: the ``Setting number of workers to N``
    line (printed when ``num_workers`` was left at 0), the overridden parameters,
    and finally the ``Starting search at 0.00s with N workers`` line.
    """
    if log.solver is None:
        return None
    if log.solver.num_workers is not None:
        return log.solver.num_workers
    params = log.solver.parameters
    if params:
        for key in ("num_workers", "num_search_workers"):
            val = params.value.get(key)
            if isinstance(val, int) and val > 0:
                return Loc(value=val, line=params.line)
    if log.search and log.search.start and log.search.start.num_workers:
        return Loc(value=log.search.start.num_workers, line=log.search.start.line)
    return None

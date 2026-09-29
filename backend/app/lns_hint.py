"""Hint: the LNS pool carried the objective search, so give it more threads.

Created 2026-09-28 from Phases G and H of the portfolio-importance study
(``benchmarks/portfolio_study/REPORT.md``, sections 7-8). When the LNS / local-search
workers delivered at least half of the time-weighted objective improvement, lowering
``num_full_subsolvers`` to half the workers beat the default in 53 of 67 held-out pairs
at 8 workers (median primal integral -28 %), in 27 of 39 at 12 workers and in 42 of 64
in 30 s runs (-13 %). Switching
individual neighborhoods off did not help, so the hint names no neighborhood.

``lns_share`` measures the pool the same way the study did (interleaved names only,
``ls_*`` variants folded into ``ls``; first-solution workers do not count). ``build_hint``
returns ``None`` whenever the evidence does not cover the run (worker count outside the
tested range, split set by the user, run not stopped by the time limit); the thresholds and texts
are in ``[lns]`` of ``knowledge/importance.toml``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cpsat_logutils import CpSatLog
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .importance import Share  # importance imports this module


class LnsHint(BaseModel):
    share: float = Field(description="Time-weighted share of the LNS/LS pool (0-1)")
    workers: int
    full: int = Field(description="Full subsolvers this run had")
    suggested_full: int
    text: str = Field(description="Markdown, from [lns].hint")
    snippet: str


def pool_names(log: CpSatLog) -> set[str]:
    if log.search is None:
        return set()
    for group in log.search.subsolvers:
        if group.category == "interleaved":
            return {e.name for e in group.subsolvers}
    return set()


def lns_share(shares: dict[str, Share], pool: set[str]) -> float:
    """Summed weighted share of the finders that belong to the interleaved pool."""
    return sum(s.weighted for who, s in shares.items() if _fold(who) in pool)


def _fold(finder: str) -> str:
    return "ls" if finder.startswith("ls_") else finder


def build_hint(
    log: CpSatLog, shares: dict[str, Share], workers: int | None, full: int, cfg: dict
) -> LnsHint | None:
    """The hint when the pool carried the run and the run is in the tested range."""
    if workers is None or not (cfg["min_workers"] <= workers <= cfg["max_workers"]):
        return None
    status = log.response.status.value if log.response and log.response.status else None
    if status is not None and status != "FEASIBLE":
        return None  # solved or proven infeasible: the study only tested runs cut by the limit
    params = log.solver.parameters.value if log.solver and log.solver.parameters else {}
    if "num_full_subsolvers" in params:
        return None  # the user already chose the split
    suggested = workers // 2
    if full <= suggested:
        return None
    share = lns_share(shares, pool_names(log))
    if share < cfg["min_share"]:
        return None
    return LnsHint(
        share=share,
        workers=workers,
        full=full,
        suggested_full=suggested,
        text=cfg["hint"].format(share=round(100 * share), full=full, suggested=suggested),
        snippet=f"solver.parameters.num_full_subsolvers = {suggested}",
    )

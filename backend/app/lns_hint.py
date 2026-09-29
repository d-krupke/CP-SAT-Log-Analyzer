"""Hint: the LNS pool carried the objective search, so give it more threads.

Created 2026-09-28 from Phases G and H of the portfolio-importance study
(``benchmarks/portfolio_study/REPORT.md``, sections 7-8). When the LNS / local-search
workers delivered at least half of the time-weighted objective improvement, lowering
``num_full_subsolvers`` to half the workers beat the default in 55 of 69 held-out pairs
at 8 workers (median primal integral -27 %), in 27 of 40 at 12 workers and in 45 of 72
in 30 s runs (-10 %). Switching
individual neighborhoods off did not help, so the hint names no neighborhood.

``lns_share`` measures the pool the same way the study did (interleaved names only; first-solution
workers do not count). A solution line may name a variant of its pool entry (``ls_restart`` for
``ls``, ``rins_lp_lns`` for ``rins/rens``, ``lb_relax_lns_bool`` for ``lb_relax_lns``);
``pool_member`` maps it back. ``build_hint``
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
    return set(log.search.subsolver_names("interleaved")) if log.search else set()


def lns_share(shares: dict[str, Share], pool: set[str]) -> float:
    """Summed weighted share of the finders that belong to the interleaved pool."""
    return sum(s.weighted for who, s in shares.items() if pool_member(who, pool) is not None)


def pool_member(finder: str, pool: set[str]) -> str | None:
    """The pool entry behind a solution line's finder name, or None if it is not in the pool.

    Exact name first; ``rins_*`` / ``rens_*`` belong to ``rins/rens``; otherwise the longest
    entry the finder extends with ``_`` (``ls_lin_restart`` -> ``ls_lin`` before ``ls``).
    """
    if finder in pool:
        return finder
    if finder.startswith(("rins_", "rens_")) and "rins/rens" in pool:
        return "rins/rens"
    prefixes = [p for p in pool if finder.startswith(p + "_")]
    return max(prefixes, key=len) if prefixes else None


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

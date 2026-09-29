"""Which full-problem strategies of the portfolio mattered for the objective search.

Created 2026-09-28 to bring the portfolio-importance study (``benchmarks/portfolio_study``,
see its ``REPORT.md``) into the analyzer. The study compared a dozen ways of ranking the
full subsolvers from one log and verified them by re-running with fewer workers; the
winner, used here, is each worker's share of the objective improvement weighted by the
time it happened. Counting solutions was tested and is misleading.

``build_ranking`` returns the ranking for the "Portfolio ranking" card, or ``None`` when
the log has nothing to rank (no objective, fewer than two full subsolvers, no improving
solution). ``objective_shares`` is also used for the plain share column of the Subsolver
contributions card. Everything is a pure read of the parsed log; the CP-SAT facts
(default order, always-keep names, reliability limits) and all texts live in
``knowledge/importance.toml``. The hint to give LNS more threads is ``lns_hint.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from cpsat_logutils import CpSatLog
from pydantic import BaseModel, Field

from .knowledge import load
from .lns_hint import LnsHint, build_hint
from .solver_info import num_workers

# Parameters that replace or filter CP-SAT's own choice of strategies.
_PORTFOLIO_PARAMS = ("subsolvers", "ignore_subsolvers", "filter_subsolvers", "extra_subsolvers")


@dataclass
class Share:
    """What one worker (any kind, LNS included) contributed to the objective."""

    share: float = 0.0  # share of the total improvement |first - last objective|
    weighted: float = 0.0  # same, each improvement weighted by its time; sums to 1
    improvements: int = 0
    last_line: int | None = None  # its latest improving solution


class RankedSubsolver(BaseModel):
    name: str
    score: float = Field(description="Time-weighted share of the objective improvement (0-1)")
    share: float = Field(description="Unweighted share of the objective improvement (0-1)")
    improvements: int
    bounds: int = Field(description="Objective-bound improvements (`Objective bounds` table)")
    verdict: str = Field(description="Key of [verdicts] in knowledge/importance.toml")
    line: int | None = Field(default=None, description="Its latest improving solution")


class WorkerChoice(BaseModel):
    """At ``workers`` threads CP-SAT runs ``full`` full subsolvers: its pick vs this log's."""

    workers: int
    full: int
    default: list[str]
    ranked: list[str]


class PortfolioRanking(BaseModel):
    ranked: list[RankedSubsolver]
    other_share: float = Field(description="Weighted share of LNS and first-solution workers")
    choices: list[WorkerChoice]
    caveats: list[str] = Field(default_factory=list, description="Markdown, most important first")
    line: int | None = Field(default=None, description="The `full problem subsolvers` line")
    lns_hint: LnsHint | None = Field(default=None, description="Give LNS more threads")


def full_subsolver_count(workers: int) -> int:
    """How many full-problem subsolvers CP-SAT 9.x starts with ``workers`` threads.

    From ``cp_model_solver.cc``; the remaining threads run first-solution heuristics until
    the first solution and LNS/local search afterwards. Checked empirically for 3-12.
    """
    if workers <= 1:
        return 1
    if workers <= 4:
        return workers - 1
    if workers <= 8:
        return workers - 2
    if workers <= 16:
        return workers - (workers // 4 + 1)
    return workers - (workers // 2 - 3)


def objective_shares(log: CpSatLog) -> dict[str, Share]:
    """Per finder: its share of the objective improvement, plain and time-weighted.

    An improvement is the objective difference to the previous solution; the first
    solution improves nothing. Shares are relative to all improvements, so they sum to 1
    over all workers. The time weight is ``t`` itself (the normalization cancels any time
    limit); if every improvement happened at time 0 the plain share is used instead.
    """
    if log.search is None or log.search.objective_sense is None:
        return {}
    sols = [
        e
        for e in log.search.events
        if e.solution_index is not None and e.objective is not None and e.time is not None
    ]
    shares: dict[str, Share] = {}
    deltas: list[tuple[str, float, float, int]] = []
    for prev, cur in zip(sols, sols[1:], strict=False):
        assert prev.objective is not None and cur.objective is not None
        delta = abs(prev.objective - cur.objective)
        if delta > 0 and cur.subsolver:
            deltas.append((cur.subsolver, delta, cur.time, cur.line))
    total = sum(d for _, d, _, _ in deltas)
    total_weighted = sum(d * t for _, d, t, _ in deltas)
    if total <= 0:
        return {}
    for who, delta, t, line in deltas:
        s = shares.setdefault(who, Share())
        s.share += delta / total
        s.weighted += delta * t / total_weighted if total_weighted > 0 else delta / total
        s.improvements += 1
        s.last_line = line
    return shares


def _full_group(log: CpSatLog) -> tuple[list[str], int | None]:
    if log.search is None:
        return [], None
    for group in log.search.subsolvers:
        if group.category == "full":
            return [e.name for e in group.subsolvers], group.line
    return [], None


def _bounds(log: CpSatLog) -> dict[str, int]:
    table = log.stats.objective_bounds
    if table is None:
        return {}
    return {r.name: n for r in table.rows if isinstance(n := r.values.get("Num"), int)}


#: Every verdict ``build_ranking`` can hand out; knowledge/importance.toml must text each.
VERDICTS = ("carried", "contributed", "backbone", "bound", "shadowed")


def _verdict(name: str, s: Share, first: bool, bounds: int, always_keep: list[str]) -> str:
    if s.weighted > 0 and first:
        return "carried"
    if s.share > 0:
        return "contributed"
    if name in always_keep:
        return "backbone"
    return "bound" if bounds > 0 else "shadowed"


def _choices(order: list[str], ranked: list[str], workers: int | None) -> list[WorkerChoice]:
    """One entry per smaller worker count at which CP-SAT would have to leave strategies out."""
    if workers is None:
        return []
    out = []
    for n in range(2, workers):
        f = full_subsolver_count(n)
        if f >= len(order):
            continue
        out.append(WorkerChoice(workers=n, full=f, default=order[:f], ranked=ranked[:f]))
    return out


def build_ranking(log: CpSatLog) -> PortfolioRanking | None:
    names, line = _full_group(log)
    if len(names) < 2:
        return None
    shares = objective_shares(log)
    if not shares:
        return None
    cfg = load("importance")
    portfolio = cfg["portfolio"]
    default_order: list[str] = portfolio["default_order"]
    position = {
        n: default_order.index(n) if n in default_order else len(default_order) for n in names
    }
    order = sorted(names, key=lambda n: (position[n], n))  # CP-SAT's own preference
    empty = Share()
    ranked_names = sorted(order, key=lambda n: -shares.get(n, empty).weighted)  # stable
    bounds = _bounds(log)
    ranked = [
        RankedSubsolver(
            name=n,
            score=shares.get(n, empty).weighted,
            share=shares.get(n, empty).share,
            improvements=shares.get(n, empty).improvements,
            bounds=bounds.get(n, 0),
            verdict=_verdict(
                n, shares.get(n, empty), i == 0, bounds.get(n, 0), portfolio["always_keep"]
            ),
            line=shares.get(n, empty).last_line,
        )
        for i, n in enumerate(ranked_names)
    ]
    full_share = sum(r.score for r in ranked)
    workers = num_workers(log)
    caveats = _caveats(log, cfg, len(names), full_share)
    n = workers.value if workers else None
    return PortfolioRanking(
        ranked=ranked,
        other_share=max(0.0, 1.0 - full_share),
        choices=_choices(order, ranked_names, n),
        caveats=caveats,
        line=line,
        lns_hint=build_hint(log, shares, n, len(names), cfg["lns"]),
    )


def _caveats(log: CpSatLog, cfg: dict, num_full: int, full_share: float) -> list[str]:
    portfolio, texts = cfg["portfolio"], cfg["caveats"]
    out = []
    if full_share < portfolio["min_full_share"]:
        out.append(texts["lns_dominated"])
    if num_full > portfolio["reliable_max_full"]:
        out.append(texts["many_full"])
    walltime = log.response.walltime.value if log.response and log.response.walltime else None
    if walltime is not None and walltime > portfolio["long_run_seconds"]:
        out.append(texts["long_run"])
    params = log.solver.parameters.value if log.solver and log.solver.parameters else {}
    if any(k in params for k in _PORTFOLIO_PARAMS):
        out.append(texts["custom_portfolio"])
    return out

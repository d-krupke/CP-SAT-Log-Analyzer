"""Per-neighborhood signals of the LNS/LS pool and the pruning rules of Phase G.

Created 2026-09-28 to extend the portfolio-importance study from the full subsolvers to the
interleaved pool (LNS neighborhoods, `ls`, `feasibility_pump`). Pure functions over a parsed
log (``cpsat_logutils``); the experiment is ``experiments/exp_g_lns.py``.

Attribution: the ``#k`` solution lines name the neighborhood (``graph_arc_lns``,
``rins/rens``) or the local-search variant (``ls_restart_decay``, ``fj_restart_...``); the
variants are folded into the worker CP-SAT lets you switch off (``ls``, ``fj``). Each name
gets the same time-weighted improvement share as the full subsolvers (``late``). The LNS
stats table adds ``Improv/Calls``: how often a neighborhood improved its local solution,
which is a denser signal than the global solution lines and breaks the ties among the many
neighborhoods that never reported a new best solution in a short run.

The only lever CP-SAT offers on the pool is ``ignore_subsolvers`` (switch a name off) plus
the thread split (``num_full_subsolvers``); a neighborhood cannot be duplicated.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise

from cpsat_logutils import CpSatLog

#: Never fewer neighborhoods than this after pruning.
KEEP_MIN = 4


@dataclass
class PoolSignal:
    name: str
    late_share: float = 0.0  # time-weighted share of the total objective improvement
    improvements: int = 0  # '#k' lines it reported
    calls: int = 0  # LNS stats: calls
    improving_calls: int = 0  # LNS stats: calls that improved its local solution

    @property
    def rate(self) -> float:
        return self.improving_calls / self.calls if self.calls else 0.0


def pool_name(finder: str) -> str:
    """The switchable worker behind a solution line's finder name."""
    if finder.startswith("ls_"):
        return "ls"
    if finder.startswith("fj_"):
        return "fj"
    return finder


def interleaved_names(log: CpSatLog) -> list[str]:
    if not log.search:
        return []
    for g in log.search.subsolvers:
        if g.category == "interleaved":
            return [e.name for e in g.subsolvers]
    return []


def pool_signals(log: CpSatLog, time_limit: float) -> dict[str, PoolSignal]:
    """Signals for every interleaved name of the log (empty names included)."""
    out = {n: PoolSignal(n) for n in interleaved_names(log)}
    if not out or not log.search:
        return out
    sols = [
        e
        for e in log.search.events
        if e.solution_index is not None
        and e.objective is not None
        and e.time is not None
    ]
    weighted: dict[str, float] = {}
    for prev, cur in pairwise(sols):
        assert (
            prev.objective is not None
            and cur.objective is not None
            and cur.time is not None
        )
        delta = abs(prev.objective - cur.objective)
        if delta > 0 and cur.subsolver:
            who = pool_name(cur.subsolver)
            weighted[who] = weighted.get(who, 0.0) + delta * min(cur.time, time_limit)
            if who in out:
                out[who].improvements += 1
    total = sum(weighted.values())
    for who, w in weighted.items():
        if who in out and total > 0:
            out[who].late_share = w / total
    table = log.stats.lns_stats
    for row in table.rows if table else []:
        cell = str(row.values.get("Improv/Calls", ""))
        if row.name in out and "/" in cell:
            a, b = cell.replace("'", "").split("/")
            out[row.name].improving_calls, out[row.name].calls = int(a), int(b)
    return out


def ranked(signals: dict[str, PoolSignal]) -> list[str]:
    """Best first: time-weighted share, then local improvement rate, then name (stable)."""
    return sorted(signals, key=lambda n: (-signals[n].late_share, -signals[n].rate, n))


def prune_idle(signals: dict[str, PoolSignal]) -> list[str]:
    """Names to ignore: every name without a share, keeping at least KEEP_MIN (best first)."""
    order = ranked(signals)
    keep = max(KEEP_MIN, sum(1 for n in order if signals[n].late_share > 0))
    return order[keep:]


def prune_top(signals: dict[str, PoolSignal], m: int) -> list[str]:
    """Contrast arm: ignore the m best names instead (never more than len - KEEP_MIN)."""
    order = ranked(signals)
    return order[: min(m, max(0, len(order) - KEEP_MIN))]


def prune_random(signals: dict[str, PoolSignal], m: int, key: str) -> list[str]:
    """Control arm: ignore m names drawn at random (deterministic in ``key``)."""
    names = sorted(signals)
    return sorted(
        random.Random(key).sample(names, min(m, max(0, len(names) - KEEP_MIN)))
    )

"""Held-out instances for Phase H: candidates, the screening rule and the per-class selection.

Created 2026-09-28 to re-test the two study results (``late`` ranking of the full subsolvers,
more LNS threads when the LNS pool carried the run) on instances the study never looked at.
The selection is mechanical so it cannot be tuned to the outcome:
    candidates  the larger half of every optimization class (the benchmark lists are ordered
                roughly by size; the small halves solve in a second), minus Phase A
    screen      one default run, 8 workers, 10 s, seed 0 (``passes_screen``: the same rule
                as the manual Phase A screen, now in code)
    select      the first ``PER_CLASS`` passing instances of each class, in list order
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cpsat_logutils import CpSatLog

from .candidates import PHASE_A
from .signals import extract_signals

#: Optimization classes of the benchmark harness (satisfaction classes have no objective).
CLASSES = (
    "bin_packing_2d", "binpacking", "cvrp", "dominating_set", "flexible_jobshop", "gap",
    "golomb_ruler", "graph_coloring", "jobshop", "max_clique", "mknapsack", "qap", "rcpsp",
    "set_covering", "strip_packing", "tsp",
)  # fmt: skip
PER_CLASS = 4
LATE_AFTER = 3.0  # seconds: the objective must still improve after this
MIN_ACTIVE_FULL = 3  # full subsolvers with a solution or a bound


def candidates(listing: dict[str, list[str]]) -> list[tuple[str, str]]:
    """The larger half of each class's instance list (``listing``: class -> names in order)."""
    seen = set(PHASE_A)
    out = []
    for p in CLASSES:
        names = listing.get(p, [])
        out += [(p, i) for i in names[len(names) // 2 :] if (p, i) not in seen]
    return out


@dataclass(frozen=True)
class Screen:
    passed: bool
    reason: str


def passes_screen(log: CpSatLog, time_limit: float = 10.0) -> Screen:
    """An active objective search in which several full subsolvers took part."""
    if log.search is None:
        return Screen(False, "no search")
    sols = [
        e
        for e in log.search.events
        if e.solution_index is not None and e.objective is not None
    ]
    if not sols:
        return Screen(False, "no solution")
    objs = [e.objective for e in sols]
    late = [
        e
        for e, prev in zip(sols[1:], objs, strict=False)
        if e.time is not None and e.time > LATE_AFTER and e.objective != prev
    ]
    if not late:
        return Screen(False, f"no improvement after {LATE_AFTER:.0f} s")
    sig = extract_signals(log, time_limit)
    active = sum(1 for s in sig.values() if s.n_solutions > 0 or s.n_bounds > 0)
    if active < MIN_ACTIVE_FULL:
        return Screen(False, f"only {active} active full subsolvers")
    return Screen(
        True, f"{len(late)} late improvements, {active} active full subsolvers"
    )


def select(
    screened: Iterable[tuple[str, str, Screen]], per_class: int = PER_CLASS
) -> list[tuple[str, str]]:
    """First ``per_class`` passing instances per class, keeping the screening order."""
    count: dict[str, int] = {}
    out = []
    for p, i, s in screened:
        if s.passed and count.get(p, 0) < per_class:
            count[p] = count.get(p, 0) + 1
            out.append((p, i))
    return out


def screen_all(
    pairs: Iterable[tuple[str, str]], log_of: Callable[[str, str], CpSatLog | None]
) -> list[tuple[str, str, Screen]]:
    """Apply the screen to every pair; ``log_of`` returns the screening log or None (failed run)."""
    out = []
    for p, i in pairs:
        log = log_of(p, i)
        out.append(
            (
                p,
                i,
                passes_screen(log) if log is not None else Screen(False, "run failed"),
            )
        )
    return out

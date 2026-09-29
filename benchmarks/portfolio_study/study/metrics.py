"""Candidate importance metrics: per-subsolver signals -> ordering (most important first).

Created 2026-09-27 for the portfolio-importance study. Every metric is a pure function
``dict[name, SubsolverSignals] -> list[str]``; ties fall back to CP-SAT's default order so
a metric with no information degrades to the default portfolio. ``METRICS`` is the
registry the experiments iterate over; add a new candidate there.
"""

from __future__ import annotations

from collections.abc import Callable

from .learn import FEATURES, feature_rows
from .signals import SubsolverSignals

Signals = dict[str, SubsolverSignals]
Metric = Callable[[Signals], list[str]]


def _order(sig: Signals, score: Callable[[SubsolverSignals], float]) -> list[str]:
    return [s.name for s in sorted(sig.values(), key=lambda s: (-score(s), s.default_rank, s.name))]


def _norm(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    return {k: (v / total if total > 0 else 0.0) for k, v in values.items()}


def default_order(sig: Signals) -> list[str]:
    return _order(sig, lambda s: 0.0)


def solution_count(sig: Signals) -> list[str]:
    return _order(sig, lambda s: float(s.n_solutions))


def improvement_share(sig: Signals) -> list[str]:
    return _order(sig, lambda s: s.improvement_share)


def late_share(sig: Signals) -> list[str]:
    return _order(sig, lambda s: s.late_share)


def last_solution_rank(sig: Signals) -> list[str]:
    """Who was still producing solutions late (chronological rank of its last solution)."""
    return _order(sig, lambda s: s.last_rank if s.last_rank is not None else -1.0)


def primal_combo(sig: Signals) -> list[str]:
    """Share of the improvement, share of the *late* improvement, and a first-solution bonus."""
    imp = _norm({n: s.improvement_share for n, s in sig.items()})
    late = _norm({n: s.late_share for n, s in sig.items()})
    return _order(sig, lambda s: 0.5 * imp[s.name] + 0.5 * late[s.name] + (0.1 if s.found_first else 0.0))


def primal_and_bound(sig: Signals) -> list[str]:
    """primal_combo plus the proving side: objective-bound and shared variable-bound improvements."""
    imp = _norm({n: s.improvement_share for n, s in sig.items()})
    late = _norm({n: s.late_share for n, s in sig.items()})
    lb = _norm({n: float(s.n_bounds) for n, s in sig.items()})
    shared = _norm({n: float(s.shared_bounds) for n, s in sig.items()})
    return _order(sig, lambda s: 0.35 * imp[s.name] + 0.35 * late[s.name] + 0.2 * lb[s.name] + 0.1 * shared[s.name])


def improvement_count(sig: Signals) -> list[str]:
    """Number of improving solutions, regardless of their size."""
    return _order(sig, lambda s: float(s.n_improvements))


def late_count(sig: Signals) -> list[str]:
    """Improving solutions after the first third of the run, then all improvements."""
    return _order(sig, lambda s: 1000.0 * s.n_late_improvements + s.n_improvements)


def mixed(sig: Signals) -> list[str]:
    """Equal-weight mix of magnitude share, count share and late-count share, plus a bonus
    for finding the final best solution."""
    imp = _norm({n: s.improvement_share for n, s in sig.items()})
    cnt = _norm({n: float(s.n_improvements) for n, s in sig.items()})
    late = _norm({n: float(s.n_late_improvements) for n, s in sig.items()})
    return _order(sig, lambda s: imp[s.name] + cnt[s.name] + late[s.name] + (0.5 if s.found_best else 0.0))


def primal_v2(sig: Signals) -> list[str]:
    """Second iteration after the Phase B ablation (see PLAN.md):
    count share + magnitude share + lateness (chronological rank of the last solution) + a
    bonus for the final best solution, minus a penalty for pure bound workers (many objective
    bound improvements, no solutions: useless when alone for the primal side)."""
    imp = _norm({n: s.improvement_share for n, s in sig.items()})
    cnt = _norm({n: float(s.n_improvements) for n, s in sig.items()})
    lb = _norm({n: float(s.n_bounds) for n, s in sig.items()})

    def score(s: SubsolverSignals) -> float:
        value = imp[s.name] + cnt[s.name] + 0.5 * s.last_rank_share + (0.25 if s.found_best else 0.0)
        if s.n_improvements == 0:
            value -= 0.5 * lb[s.name]
        return value

    return _order(sig, score)


# Mean solo quality per name over the Phase B instances (filled from exp_b_learn output);
# a *name-only* baseline that ignores the log. Names not listed get 0.
NAME_PRIOR: dict[str, float] = {  # exp_b_learn, 12 instances, solo seeds 0-2 (2026-09-27)
    "default_lp": 0.74, "fixed": 0.36, "quick_restart_no_lp": 0.34, "quick_restart": 0.28,
    "no_lp": -0.04, "max_lp": -0.05, "core": -0.42, "reduced_costs": -0.83,
}


def name_prior(sig: Signals) -> list[str]:
    """Fixed order learned from the ablation data, independent of the log at hand."""
    return _order(sig, lambda s: NAME_PRIOR.get(s.name.replace("max_lp_sym", "max_lp"), 0.0))


def primal_v3(sig: Signals) -> list[str]:
    """primal_v2 blended with the name prior: the log decides, the prior breaks near-ties and
    fills in for subsolvers that were shadowed (no solutions) in the normal run."""
    v2 = {n: i for i, n in enumerate(primal_v2(sig))}
    k = max(len(sig) - 1, 1)
    return _order(
        sig,
        lambda s: 1.0 - v2[s.name] / k + 0.3 * NAME_PRIOR.get(s.name.replace("max_lp_sym", "max_lp"), 0.0),
    )


def primal_v4(sig: Signals) -> list[str]:
    """Third iteration, after the Phase C verification of primal_v2 (see PLAN.md).
    Magnitude only: counting improvements rewards workers that polish in tiny steps
    (quick_restart on cvrp, core on mknapsack), which are worthless alone. Score = share of
    the total improvement + share of the *late* improvement (magnitude weighted by time),
    and subsolvers without any improvement fall back to the learned name prior (a shadowed
    `default_lp` is still a good bet) minus the pure-bound-worker penalty."""
    imp = _norm({n: s.improvement_share for n, s in sig.items()})
    late = _norm({n: s.late_share for n, s in sig.items()})
    lb = _norm({n: float(s.n_bounds) for n, s in sig.items()})

    def score(s: SubsolverSignals) -> float:
        value = imp[s.name] + late[s.name]
        if s.n_improvements == 0:
            value += 0.05 * NAME_PRIOR.get(s.name.replace("max_lp_sym", "max_lp"), 0.0) - 0.1 * lb[s.name]
        return value

    return _order(sig, score)


# Ridge weights (alpha=1) from exp_b_learn on all 12 Phase B instances, solo seeds 0-2.
LEARNED_WEIGHTS: dict[str, float] = {
    "improvement_share": 1.062, "count_share": -0.025, "late_count_share": 0.370,
    "found_first": -0.384, "found_best": -0.119, "last_rank_share": 0.595,
    "bounds_share": -0.304, "shared_bounds_share": 0.595, "conflict_share": -0.499,
    "default_pos": 0.532,
}


def learned(sig: Signals) -> list[str]:
    """Frozen ridge-regression weights on the ``learn.FEATURES`` (fitted in Phase B)."""
    rows = feature_rows(sig)
    w = [LEARNED_WEIGHTS[f] for f in FEATURES]
    return _order(sig, lambda s: float(sum(x * wi for x, wi in zip(rows[s.name], w, strict=True))))


ANCHORS = ("default_lp",)


def late_anchor(sig: Signals) -> list[str]:
    """`late` with default_lp pinned to the top. Phase B/C data: default_lp is the only
    subsolver that is never bad alone (worst solo result 1.66x the best, mean regret 0.06)
    and removing it from a portfolio costs +0.5 relative primal integral on average, while
    the log-based ranking sometimes drops it when it was shadowed (no solutions) in the
    normal run."""
    order = late_share(sig)
    return [n for n in ANCHORS if n in order] + [n for n in order if n not in ANCHORS]


def activity(sig: Signals) -> list[str]:
    """Control metric: raw search activity (conflicts). Expected to be a poor predictor."""
    return _order(sig, lambda s: float(s.conflicts))


METRICS: dict[str, Metric] = {
    "default": default_order,
    "n_solutions": solution_count,
    "improvement": improvement_share,
    "late": late_share,
    "last_rank": last_solution_rank,
    "primal_combo": primal_combo,
    "primal_bound": primal_and_bound,
    "count": improvement_count,
    "late_count": late_count,
    "mixed": mixed,
    "primal_v2": primal_v2,
    "name_prior": name_prior,
    "primal_v3": primal_v3,
    "primal_v4": primal_v4,
    "late_anchor": late_anchor,
    "learned": learned,
    "activity": activity,
}

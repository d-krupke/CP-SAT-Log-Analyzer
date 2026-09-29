"""Phase D, offline: which *pair-selection rule* picks the best pair, given the all-pairs
ground truth at 3 workers (exp_d_pairs)? Created 2026-09-28 to test the "always keep" and
"complementarity" hypotheses cheaply before running them through the full protocol.

A rule maps the signals of an 8-worker log to two names; it is scored by the seed-averaged
primal integral of that pair minus the best pair's (regret), over instances and the log
seeds 0 and 1.
    uv run python -m portfolio_study.experiments.exp_d_rules
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from itertools import combinations
from statistics import mean

from portfolio_study.experiments.exp_d_pairs import LP_LEVEL, _names
from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS, late_share
from portfolio_study.study.runner import RunConfig
from portfolio_study.study.signals import SubsolverSignals, extract_signals
from portfolio_study.study.store import InstanceRuns

Sig = dict[str, SubsolverSignals]


def _lp(name: str) -> int:
    return LP_LEVEL.get(name, 1)


def rule_late(sig: Sig) -> tuple[str, str]:
    a, b = late_share(sig)[:2]
    return a, b


def rule_anchor(sig: Sig) -> tuple[str, str]:
    """default_lp plus the best other by late."""
    rest = [n for n in late_share(sig) if n != "default_lp"]
    return ("default_lp", rest[0]) if "default_lp" in sig else (rest[0], rest[1])


def rule_anchor_fixed(sig: Sig) -> tuple[str, str]:
    """default_lp plus fixed when the model has one, else the best other by late."""
    if "fixed" in sig:
        return "default_lp", "fixed"
    return rule_anchor(sig)


def rule_diverse(sig: Sig) -> tuple[str, str]:
    """best by late, then the best by late with a different LP level."""
    order = late_share(sig)
    first = order[0]
    for n in order[1:]:
        if _lp(n) != _lp(first):
            return first, n
    return first, order[1]


def rule_anchor_diverse(sig: Sig) -> tuple[str, str]:
    """default_lp plus the best by late among the non-LP-level-1 names (no_lp/core/max_lp/...)."""
    if "default_lp" not in sig:
        return rule_diverse(sig)
    for n in late_share(sig):
        if _lp(n) != 1:
            return "default_lp", n
    return rule_anchor(sig)


def rule_anchor_fixed_diverse(sig: Sig) -> tuple[str, str]:
    """fixed (if present) as the anchor on scheduling models, else default_lp; partner = best
    by late with a different LP level from the anchor."""
    anchor = "fixed" if "fixed" in sig else "default_lp"
    if anchor not in sig:
        return rule_diverse(sig)
    for n in late_share(sig):
        if n != anchor and _lp(n) != _lp(anchor):
            return anchor, n
    return rule_anchor(sig)


def rule_default(sig: Sig) -> tuple[str, str]:
    a, b = METRICS["default"](sig)[:2]
    return a, b


RULES: dict[str, Callable[[Sig], tuple[str, str]]] = {
    "default": rule_default, "late": rule_late, "anchor(dlp)": rule_anchor,
    "anchor(dlp,fixed)": rule_anchor_fixed, "diverse": rule_diverse,
    "anchor+diverse": rule_anchor_diverse, "fixed/dlp+diverse": rule_anchor_fixed_diverse,
}


def main() -> None:
    regret: dict[str, list[float]] = defaultdict(list)
    rel: dict[str, list[float]] = defaultdict(list)
    hits: dict[str, int] = defaultdict(int)
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        names = _names(runs)
        avg = {}
        for pair in combinations(names, 2):
            vals = [runs.primal(RunConfig(p, i, workers=3, time_limit=10, seed=s, subsolvers=pair)).integral for s in (0, 1)]
            avg[frozenset(pair)] = mean(vals)
        best = min(avg.values())
        for seed in (0, 1):
            sig = extract_signals(runs.log(RunConfig(p, i, workers=8, time_limit=10, seed=seed).key), 10.0)
            for name, rule in RULES.items():
                pick = frozenset(rule(sig))
                regret[name].append(avg[pick] - best)
                rel[name].append(avg[pick] / max(best, 1e-3))
                hits[name] += avg[pick] <= best + 1e-9
    print(f"{'rule':20s} {'mean regret':>11s} {'max regret':>10s} {'mean PI/best':>12s} {'exact':>5s}  (24 picks: 12 instances x 2 log seeds)")
    for name in RULES:
        print(f"{name:20s} {mean(regret[name]):11.3f} {max(regret[name]):10.2f} {mean(rel[name]):12.2f} {hits[name]:5d}")


if __name__ == "__main__":
    main()

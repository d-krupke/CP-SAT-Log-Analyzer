"""Phase D: all pairs of full subsolvers at 3 workers (F(3) = 2, plus one LNS thread).

Created 2026-09-27 to learn *interdependencies*: is the best pair the two best solo
workers, or do complementary workers (LP vs no-LP) beat them? And which name is in the
best pair most often / hurts most when missing (the "always keep" question)?
    uv run python -m portfolio_study.experiments.exp_d_pairs [seed ...]          # run
    uv run python -m portfolio_study.experiments.exp_d_pairs --report [seed ...] # analyse
Pairs already stored by Phase C (same name set, any order) are reused.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from itertools import combinations
from statistics import mean

from portfolio_study.experiments.exp_b_report import ground_truth
from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig, run_jobs
from portfolio_study.study.signals import extract_signals
from portfolio_study.study.store import InstanceRuns

# linearization_level per name in cp_model_search.cc (0 = no LP relaxation)
LP_LEVEL = {"no_lp": 0, "core": 0, "quick_restart_no_lp": 0, "default_lp": 1, "fixed": 1, "quick_restart": 1,
            "max_lp": 2, "max_lp_sym": 2, "reduced_costs": 2, "pseudo_costs": 2, "lb_tree_search": 2}


def _names(runs: InstanceRuns) -> list[str]:
    sig = extract_signals(runs.log(RunConfig(runs.problem, runs.instance, workers=8, time_limit=10, seed=0).key), 10.0)
    return sorted(sig, key=lambda k: sig[k].default_rank)


def pair_jobs(problem: str, instance: str, seeds: tuple[int, ...]) -> list[RunConfig]:
    runs = InstanceRuns(problem, instance)
    jobs = [RunConfig(problem, instance, workers=3, time_limit=10, seed=s, subsolvers=pair)
            for s in seeds for pair in combinations(_names(runs), 2)]
    return [j for j in jobs if runs.find(j) is None]


def report(seeds: tuple[int, ...]) -> None:
    in_best: dict[str, int] = defaultdict(int)
    marginal: dict[str, list[float]] = defaultdict(list)   # z-scored PI of pairs containing the name
    diverse_vs_same: list[tuple[float, float]] = []
    top2_hits = {"late": 0, "solo": 0, "default": 0}
    n_inst = 0
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        names = _names(runs)
        pi: dict[frozenset, list[float]] = defaultdict(list)
        for s in seeds:
            for pair in combinations(names, 2):
                cfg = RunConfig(p, i, workers=3, time_limit=10, seed=s, subsolvers=pair)
                if runs.find(cfg) is not None:
                    pi[frozenset(pair)].append(runs.primal(cfg).integral)
        if len(pi) < len(names) * (len(names) - 1) // 2:
            continue
        n_inst += 1
        avg = {k: mean(v) for k, v in pi.items()}
        vals = list(avg.values())
        mu = mean(vals)
        sd = (mean((v - mu) ** 2 for v in vals)) ** 0.5 or 1.0
        best = min(avg, key=lambda k: avg[k])
        default_pair = frozenset(names[:2])
        print(f"\n{p}/{i}: best pair {'+'.join(sorted(best))} PI={avg[best]:.2f}; default pair "
              f"{'+'.join(sorted(default_pair))} PI={avg[default_pair]:.2f}")
        for k in sorted(avg, key=lambda k: avg[k])[:4]:
            print(f"   {'+'.join(sorted(k)):32s} {avg[k]:.2f}")
        for n in names:
            if n in best:
                in_best[n] += 1
            marginal[n].extend((avg[k] - mu) / sd for k in avg if n in k)
        for k, v in avg.items():
            a, b = sorted(k)
            same = LP_LEVEL.get(a, 1) == LP_LEVEL.get(b, 1)
            diverse_vs_same.append((0.0 if same else 1.0, (v - mu) / sd))
        # does the metric's top-2 (from the seed-0 8-worker log) hit the best pair?
        sig = extract_signals(runs.log(RunConfig(p, i, workers=8, time_limit=10, seed=0).key), 10.0)
        top2 = frozenset(METRICS["late"](sig)[:2])
        _, solo, _ = ground_truth(runs, names, (0, 1, 2))
        for name, pair in (("late", top2), ("solo", frozenset(solo[:2])), ("default", default_pair)):
            top2_hits[name] += pair == best
            print(f"   {name:8s} top-2 {'+'.join(sorted(pair)):32s} PI={avg[pair]:.2f} ({avg[pair] - avg[best]:+.2f} vs best)")
    print(f"\n=== {n_inst} instances, seeds {seeds} ===")
    print("in best pair:", dict(sorted(in_best.items(), key=lambda kv: -kv[1])))
    print("mean z-scored PI of pairs containing the name (negative = good partner):")
    for n, v in sorted(marginal.items(), key=lambda kv: mean(kv[1])):
        print(f"   {n:20s} {mean(v):+.2f}  (n={len(v)})")
    div = [z for d, z in diverse_vs_same if d]
    same = [z for d, z in diverse_vs_same if not d]
    print(f"pairs with different LP level: mean z {mean(div):+.2f} (n={len(div)}); same LP level: {mean(same):+.2f} (n={len(same)})")
    print("top-2 equals the best pair:", top2_hits)


if __name__ == "__main__":
    args = sys.argv[1:]
    do_report = "--report" in args
    seeds = tuple(int(s) for s in args if s != "--report") or (0,)
    if do_report:
        report(seeds)
    else:
        run_jobs([j for p, i in PHASE_B for j in pair_jobs(p, i, seeds)], budget=12)

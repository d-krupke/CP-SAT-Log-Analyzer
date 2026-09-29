"""Phase E: the blacklist direction as a paired contrast.

Created 2026-09-27. Leave-one-out at 7 workers was within noise, so instead of "remove one"
vs default we compare two removals against each other: at n workers, `ignore_subsolvers`
= the *most* important name of the default set (by `late`, from the 8-worker log of the
same seed) vs the *least* important one. CP-SAT refills the freed slot with the next
default name, so both arms have F(n) full subsolvers. If the metric means anything,
removing the best must hurt more than removing the worst.
    uv run python -m portfolio_study.experiments.exp_e_blacklist [--report] [seed ...]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from statistics import mean

from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig, default_full_count, run_jobs
from portfolio_study.study.signals import extract_signals
from portfolio_study.study.store import InstanceRuns

WORKERS = (4, 6)


def arms(problem: str, instance: str, seed: int, n: int) -> tuple[RunConfig, RunConfig, RunConfig] | None:
    runs = InstanceRuns(problem, instance)
    base = RunConfig(problem, instance, workers=8, time_limit=10, seed=seed)
    if not runs.has(base):
        return None
    sig = extract_signals(runs.log(base.key), 10.0)
    f = default_full_count(n)
    default_set = sorted(sig, key=lambda k: sig[k].default_rank)[:f]
    order = [x for x in METRICS["late"](sig) if x in default_set]
    if sig[order[0]].late_share == 0.0:  # no information in the log for these names
        return None
    mk = lambda ign: RunConfig(problem, instance, workers=n, time_limit=10, seed=seed, ignore=(ign,))
    return RunConfig(problem, instance, workers=n, time_limit=10, seed=seed), mk(order[0]), mk(order[-1])


def report(seeds: tuple[int, ...]) -> None:
    diffs: dict[int, list[float]] = defaultdict(list)
    wins = losses = 0
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        for seed in seeds:
            for n in WORKERS:
                a = arms(p, i, seed, n)
                if a is None or any(runs.find(c) is None for c in a):
                    continue
                d, best, worst = (runs.primal(c).integral for c in a)
                diff = best - worst  # positive = removing the best hurt more
                diffs[n].append(diff)
                wins += diff > 0
                losses += diff < 0
                print(f"{p}/{i} s{seed} n={n}: default {d:.2f}  -best({a[1].ignore[0]}) {best:.2f}  -worst({a[2].ignore[0]}) {worst:.2f}  diff {diff:+.2f}")
    print(f"\nremove-best worse than remove-worst: {wins} of {wins + losses} pairs")
    for n, v in diffs.items():
        print(f"  n={n}: mean diff {mean(v):+.3f} over {len(v)} pairs")


if __name__ == "__main__":
    args = sys.argv[1:]
    do_report = "--report" in args
    seeds = tuple(int(s) for s in args if s != "--report") or (0,)
    if do_report:
        report(seeds)
    else:
        jobs = [c for p, i in PHASE_B for s in seeds for n in WORKERS for c in (arms(p, i, s, n) or ())]
        run_jobs([j for j in jobs if InstanceRuns(j.problem, j.instance).find(j) is None], budget=12)

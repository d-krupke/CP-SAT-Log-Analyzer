"""Phase B report: ablation ground truth vs. the log signals of the normal run.

Per instance: for every full subsolver X the solo result (2 workers, X plus one LNS thread)
averaged over the available seeds, and the leave-one-out result (7 workers without X, seed 0
only; it turned out to be within noise), next to the signals from the 8-worker seed-0 log.
Then, per metric, the Spearman correlation between the metric's ordering and the ground
truth orderings, and the metric's stability between the seed-0 and seed-1 normal runs.
    uv run python -m portfolio_study.experiments.exp_b_report [seed ...]
"""

from __future__ import annotations

import sys
from statistics import mean

from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig
from portfolio_study.study.signals import extract_signals, full_subsolver_names
from portfolio_study.study.store import InstanceRuns


def spearman(a: list[str], b: list[str]) -> float:
    """Rank correlation between two orderings of the same names."""
    n = len(a)
    if n < 2:
        return 0.0
    ra = {x: i for i, x in enumerate(a)}
    rb = {x: i for i, x in enumerate(b)}
    d2 = sum((ra[x] - rb[x]) ** 2 for x in a)
    return 1 - 6 * d2 / (n * (n * n - 1))


def ground_truth(runs: InstanceRuns, names: list[str], seeds: tuple[int, ...], measure: str = "integral") -> tuple[list[str], list[str], dict]:
    """Orderings by solo quality (mean over seeds; best first) and by leave-one-out damage
    (seed 0; worse without X first). Names without runs are left out."""
    loo, solo = {}, {}
    for x in names:
        others = tuple(n for n in names if n != x)
        c_loo = RunConfig(runs.problem, runs.instance, workers=7, time_limit=10, seed=0, subsolvers=others)
        if runs.has(c_loo):
            loo[x] = getattr(runs.primal(c_loo), measure)
        vals = []
        for seed in seeds:
            c_solo = RunConfig(runs.problem, runs.instance, workers=2, time_limit=10, seed=seed, subsolvers=(x,))
            if runs.has(c_solo):
                vals.append(getattr(runs.primal(c_solo), measure))
        if vals:
            solo[x] = mean(vals)
    loo_order = sorted(loo, key=lambda x: -loo[x])
    solo_order = sorted(solo, key=lambda x: solo[x])
    return loo_order, solo_order, {"loo": loo, "solo": solo}


def main(seeds: tuple[int, ...]) -> None:
    corr: dict[str, dict[str, list[float]]] = {m: {"loo": [], "solo": [], "stable": []} for m in METRICS}
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        base = RunConfig(p, i, workers=8, time_limit=10, seed=0)
        log = runs.log(base.key)
        names = full_subsolver_names(log)
        sig = extract_signals(log, 10.0)
        base1 = RunConfig(p, i, workers=8, time_limit=10, seed=1)
        sig1 = extract_signals(runs.log(base1.key), 10.0) if runs.has(base1) else None
        loo_order, solo_order, gt = ground_truth(runs, names, seeds)
        if len(solo_order) < len(names):
            print(f"{p}/{i}: incomplete ({len(solo_order)}/{len(names)} solo runs)")
            continue
        p8 = runs.primal(base)
        d2 = [runs.primal(RunConfig(p, i, workers=2, time_limit=10, seed=s)).integral for s in seeds if runs.has(RunConfig(p, i, workers=2, time_limit=10, seed=s))]
        print(f"\n{p}/{i}  best={runs.best_known:g}  8w: gap={p8.final_gap:.3f} PI={p8.integral:.2f}  2w default PI={mean(d2) if d2 else float('nan'):.2f}")
        print(f"  {'subsolver':20s} {'solo-PI':>8s} {'LOO-PI':>7s} | share  late  imp  lastrank  lb  shared")
        for x in names:
            s = sig[x]
            print(f"  {x:20s} {gt['solo'].get(x, float('nan')):8.2f} {gt['loo'].get(x, float('nan')):7.2f} | "
                  f"{s.improvement_share:5.2f} {s.late_share:5.2f} {s.n_improvements:4d} {s.last_rank_share:8.2f} {s.n_bounds:4d} {s.shared_bounds:7d}")
        print(f"  ground truth  solo: {solo_order}\n                LOO:  {loo_order}")
        for m, f in METRICS.items():
            order = f(sig)
            corr[m]["solo"].append(spearman(order, solo_order))
            if len(loo_order) == len(names):
                corr[m]["loo"].append(spearman(order, loo_order))
            if sig1 is not None:
                corr[m]["stable"].append(spearman(order, f(sig1)))
            print(f"  {m:14s} {order}  rho_solo={corr[m]['solo'][-1]:+.2f}")
    print("\n=== mean Spearman over instances (solo = ground truth; stable = seed-0 vs seed-1 log) ===")
    for m in METRICS:
        c = corr[m]
        if c["solo"]:
            print(f"  {m:14s} solo={mean(c['solo']):+.3f}  loo={mean(c['loo']) if c['loo'] else float('nan'):+.3f}  "
                  f"stable={mean(c['stable']) if c['stable'] else float('nan'):+.3f}  (n={len(c['solo'])})")


if __name__ == "__main__":
    main(tuple(int(s) for s in sys.argv[1:]) or (0,))

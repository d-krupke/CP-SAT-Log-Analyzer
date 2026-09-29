"""Phase B, learned metric: fit ridge weights from the 8-worker log features to the ablation
ground truth and check them leave-one-instance-out against the hand-made metrics.
    uv run python -m portfolio_study.experiments.exp_b_learn [--target solo|loo] [seed ...]
"""

from __future__ import annotations

import sys
from statistics import mean

import numpy as np

from portfolio_study.experiments.exp_b_report import ground_truth, spearman
from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.learn import FEATURES, feature_rows, loio, ridge, zscore
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig
from portfolio_study.study.signals import extract_signals, full_subsolver_names
from portfolio_study.study.store import InstanceRuns


def main(seeds: tuple[int, ...], target: str) -> None:
    datasets, truths, labels, sigs = [], [], [], []
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        base = RunConfig(p, i, workers=8, time_limit=10, seed=0)
        log = runs.log(base.key)
        names = full_subsolver_names(log)
        loo_order, solo_order, gt = ground_truth(runs, names, seeds)
        values = gt["solo"] if target == "solo" else gt["loo"]
        if len(values) < len(names):
            continue
        sig = extract_signals(log, 10.0)
        # solo: small integral = good -> negate; loo: large integral without X = X important
        y = zscore({k: (-v if target == "solo" else v) for k, v in values.items()})
        datasets.append((feature_rows(sig), y))
        truths.append(solo_order if target == "solo" else loo_order)
        labels.append(f"{p}/{i}")
        sigs.append(sig)
    if len(datasets) < 3:
        print("not enough complete instances")
        return
    for alpha in (0.3, 1.0, 3.0):
        preds = loio(datasets, alpha)
        rhos = [spearman(pred, truth) for pred, truth in zip(preds, truths, strict=True)]
        print(f"alpha={alpha}: LOIO Spearman vs {target} = {mean(rhos):+.3f}  per instance: " + " ".join(f"{r:+.2f}" for r in rhos))
    print("hand-made metrics on the same instances:")
    for m, f in METRICS.items():
        rhos = [spearman(f(sig), truth) for sig, truth in zip(sigs, truths, strict=True)]
        print(f"  {m:14s} {mean(rhos):+.3f}")
    by_name: dict[str, list[float]] = {}
    for _, t in datasets:
        for k, v in t.items():
            by_name.setdefault(k.replace("max_lp_sym", "max_lp"), []).append(v)
    print(f"mean {target} z-score per name (a name-only prior):")
    for k, v in sorted(by_name.items(), key=lambda kv: -mean(kv[1])):
        print(f"  {k:20s} {mean(v):+.2f}  (n={len(v)})")
    X = np.vstack([x for f, _ in datasets for x in f.values()])
    y = np.array([t[k] for f, t in datasets for k in f])
    fit = ridge(X, y, 1.0)
    print("full-fit weights (alpha=1):")
    for name, w in zip(FEATURES, fit.weights, strict=True):
        print(f"  {name:20s} {w:+.3f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    target = "solo"
    if args and args[0] == "--target":
        target = args[1]
        args = args[2:]
    main(tuple(int(s) for s in args) or (0,), target)

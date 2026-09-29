"""Phase C report: per metric, how the top-F(n) portfolio compares with the default one.

For every (instance, seed, n) pair with both runs present: sign of the difference in final
gap and in primal integral (ranked minus default; negative = ranked better), aggregated as
wins/ties/losses and mean differences per metric, and per worker count for the metrics.
    uv run python -m portfolio_study.experiments.exp_c_report [--metrics a,b] [-v] [seed ...]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from statistics import mean

from portfolio_study.experiments.exp_c_verify import WORKERS
from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig, default_full_count
from portfolio_study.study.signals import extract_signals
from portfolio_study.study.store import InstanceRuns


def sign(x: float, eps: float = 1e-9) -> str:
    return "win" if x < -eps else ("loss" if x > eps else "tie")


def main(seeds: tuple[int, ...], metrics: list[str], verbose: bool, base: int = 8,
         workers: tuple[int, ...] = WORKERS, time_limit: float = 10.0) -> None:
    T = time_limit
    agg: dict[str, dict[str, list]] = {m: defaultdict(list) for m in metrics}
    per_n: dict[tuple[str, int], dict[str, list]] = defaultdict(lambda: defaultdict(list))
    per_inst: dict[tuple[str, str], list[float]] = defaultdict(list)
    for p, i in PHASE_B:
        runs = InstanceRuns(p, i)
        for seed in seeds:
            base_cfg = RunConfig(p, i, workers=base, time_limit=T, seed=seed)
            if not runs.has(base_cfg):
                continue
            sig = extract_signals(runs.log(base_cfg.key), T)
            by_default = sorted(sig, key=lambda k: sig[k].default_rank)
            for n in workers:
                f = default_full_count(n)
                d = RunConfig(p, i, workers=n, time_limit=T, seed=seed)
                if not runs.has(d):
                    continue
                pd = runs.primal(d)
                line = [f"{p}/{i} s{seed} n={n} F={f}: default gap={pd.final_gap:.3f} PI={pd.integral:.2f}"]
                for m in metrics:
                    top = tuple(METRICS[m](sig)[:f])
                    c = RunConfig(p, i, workers=n, time_limit=T, seed=seed, subsolvers=top)
                    if runs.find(c) is None:
                        continue
                    pr = runs.primal(c)
                    dgap, dpi = pr.final_gap - pd.final_gap, pr.integral - pd.integral
                    if set(top) == set(by_default[:f]):
                        # Same portfolio as the default: the difference is pure timing noise.
                        agg[m]["same_pi"].append(dpi)
                        agg[m]["same_gap"].append(dgap)
                        if verbose:
                            line.append(f"    {m:13s} {'+'.join(top):40s} = default set, noise PI {dpi:+.2f}")
                        continue
                    agg[m]["gap"].append(dgap)
                    agg[m]["pi"].append(dpi)
                    agg[m]["gap_sign"].append(sign(dgap))
                    agg[m]["pi_sign"].append(sign(dpi))
                    per_n[(m, n)]["gap"].append(dgap)
                    per_n[(m, n)]["pi"].append(dpi)
                    per_n[(m, n)]["pi_sign"].append(sign(dpi))
                    per_inst[(m, f"{p}/{i}")].append(dpi)
                    line.append(f"    {m:13s} {'+'.join(top):40s} gap={pr.final_gap:.3f} ({dgap:+.3f}) PI={pr.integral:.2f} ({dpi:+.2f})")
                if verbose:
                    print("\n".join(line))
    print("\n=== ranked top-F vs default, over all (instance, seed, n); negative = ranked better ===")
    print("(pairs whose top-F set equals the default set are excluded and reported as noise)")
    print(f"{'metric':14s} {'n':>3s} | final gap: W/T/L   mean    | primal integral: W/T/L   mean   | same-set pairs: n  mean|dPI|")
    for m in metrics:
        a = agg[m]
        if not a["gap"] and not a["same_pi"]:
            continue
        g, pi = a["gap_sign"], a["pi_sign"]
        noise = mean(abs(x) for x in a["same_pi"]) if a["same_pi"] else float("nan")
        gm = mean(a["gap"]) if a["gap"] else float("nan")
        pm = mean(a["pi"]) if a["pi"] else float("nan")
        print(f"{m:14s} {len(a['gap']):3d} | {g.count('win'):2d}/{g.count('tie'):2d}/{g.count('loss'):2d}  {gm:+.4f} | "
              f"{pi.count('win'):2d}/{pi.count('tie'):2d}/{pi.count('loss'):2d}  {pm:+.3f}  | {len(a['same_pi']):3d}  {noise:.3f}")
    print("\n=== per worker count (mean PI difference, W/T/L on PI) ===")
    for m in metrics:
        row = []
        for n in workers:
            a = per_n.get((m, n))
            if a and a["pi"]:
                s = a["pi_sign"]
                row.append(f"n={n}: {mean(a['pi']):+.3f} ({s.count('win')}/{s.count('tie')}/{s.count('loss')})")
        if row:
            print(f"{m:14s} " + "  ".join(row))
    print("\n=== per instance (mean PI difference over seeds and n; W/L) ===")
    for m in metrics:
        row = []
        for p, i in PHASE_B:
            d = per_inst.get((m, f"{p}/{i}"))
            if d:
                row.append(f"{i[:9]:9s} {mean(d):+.2f} ({sum(x < 0 for x in d)}/{sum(x > 0 for x in d)})")
        if row:
            print(f"{m:14s} " + " | ".join(row))


if __name__ == "__main__":
    args = sys.argv[1:]
    metrics = [m for m in METRICS if m != "default"]
    verbose = False
    if "-v" in args:
        verbose = True
        args.remove("-v")
    if args and args[0] == "--metrics":
        metrics = args[1].split(",")
        args = args[2:]
    base, workers, time_limit = 8, WORKERS, 10.0
    if "--base" in args:
        k = args.index("--base"); base = int(args[k + 1]); del args[k:k + 2]
    if "--workers" in args:
        k = args.index("--workers"); workers = tuple(int(w) for w in args[k + 1].split(",")); del args[k:k + 2]
    if "--time" in args:
        k = args.index("--time"); time_limit = float(args[k + 1]); del args[k:k + 2]
    main(tuple(int(s) for s in args) or (0,), metrics, verbose, base, workers, time_limit)

"""Phase C: verification. For every kept instance, seed and worker count n in {2,3,4,6,7},
run the default portfolio and, per metric, the top-F(n) subsolvers of the ordering that
the metric derives from the 8-worker log of the same seed. Runs are cached by the name
set, so metrics that agree share runs.
    uv run python -m portfolio_study.experiments.exp_c_verify [--metrics a,b] [--base 12] \
        [--workers 2,4,6] [--time 30] [seed ...]
--base is the worker count of the log the metric reads (default 8; missing base logs are
run first), --time the time limit of all runs (default 10 s).
"""

from __future__ import annotations

import sys

from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import RunConfig, default_full_count, run_jobs
from portfolio_study.study.signals import extract_signals
from portfolio_study.study.store import InstanceRuns

WORKERS = (2, 3, 4, 6, 7)


def base_config(problem: str, instance: str, seed: int, base: int = 8, time_limit: float = 10.0) -> RunConfig:
    return RunConfig(problem, instance, workers=base, time_limit=time_limit, seed=seed)


def verify_jobs(problem: str, instance: str, seed: int, metrics: list[str], time_limit: float = 10.0,
                base: int = 8, workers: tuple[int, ...] = WORKERS) -> list[RunConfig]:
    runs = InstanceRuns(problem, instance)
    sig = extract_signals(runs.log(base_config(problem, instance, seed, base, time_limit).key), time_limit)
    jobs = []
    for n in workers:
        f = default_full_count(n)
        jobs.append(RunConfig(problem, instance, workers=n, time_limit=time_limit, seed=seed))
        for m in metrics:
            top = tuple(METRICS[m](sig)[:f])
            jobs.append(RunConfig(problem, instance, workers=n, time_limit=time_limit, seed=seed, subsolvers=top))
    # de-duplicate by name set (order is irrelevant to CP-SAT) and reuse equivalent stored runs
    unique = {(j.workers, frozenset(j.subsolvers)): j for j in jobs}
    return [j for j in unique.values() if runs.find(j) is None]


if __name__ == "__main__":
    args = sys.argv[1:]
    metrics = [m for m in METRICS if m != "default"]
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
    instances = PHASE_B
    if "--only" in args:  # comma-separated instance names, e.g. --only ta61,order12
        k = args.index("--only"); only = set(args[k + 1].split(",")); del args[k:k + 2]
        instances = [(p, i) for p, i in PHASE_B if i in only]
    seeds = tuple(int(s) for s in args) or (0,)
    run_jobs([base_config(p, i, s, base, time_limit) for p, i in instances for s in seeds], budget=12)
    jobs = [j for p, i in instances for s in seeds for j in verify_jobs(p, i, s, metrics, time_limit, base, workers)]
    run_jobs(jobs, budget=12)

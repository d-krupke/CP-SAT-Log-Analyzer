"""Phase G: does the log tell which LNS neighborhoods to keep, and when to give LNS more threads?

Created 2026-09-28 (third session). Two levers exist on the interleaved pool
(study/lns.py): switching neighborhoods off with ``ignore_subsolvers`` (verified on ta61:
ignoring 6 of 13 names doubles the calls of the remaining ones) and moving threads from
full subsolvers to the pool with ``num_full_subsolvers`` (nf4: 1.9x the LNS calls, nf2: 2.7x).

Arms, all at 8 workers, paired with the default run of the same instance and seed. The
reference log is the default run of the *partner seed* (0<->1, 2<->3): the selection is read
from one run and tested on an independent one, as a user would do.
    prune   ignore every pool name without a share in the reference log (keep >= 4)
    random  ignore the same number of names at random            (control: fewer names)
    top     ignore the same number of the *best* names            (contrast: must hurt)
    nf4/nf2 num_full_subsolvers = 4 / 2: more LNS threads, CP-SAT's first full names
Measure: primal integral (PI), as in all phases; sign tests on paired differences.

    uv run python -m portfolio_study.experiments.exp_g_lns [--time 30] [--report] [seed ...]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from math import comb
from statistics import mean, median

from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.lns import pool_signals, prune_idle, prune_random, prune_top
from portfolio_study.study.runner import RunConfig, run_jobs
from portfolio_study.study.store import InstanceRuns

LONG = [
    ("jobshop", "ta61"),
    ("cvrp", "A-n46-k7"),
    ("mknapsack", "mknapcb5_00"),
    ("golomb_ruler", "order12"),
    ("set_covering", "scpcyc09"),
    ("qap", "nug15"),
]
ARMS = ("prune", "random", "top", "nf4", "nf2")


def instances(t: float) -> list[tuple[str, str]]:
    return LONG if t > 10 else PHASE_B


def default(p: str, i: str, t: float, seed: int) -> RunConfig:
    return RunConfig(p, i, workers=8, time_limit=t, seed=seed)


def arms(
    p: str, i: str, t: float, seed: int, runs: InstanceRuns
) -> dict[str, RunConfig]:
    """The arm configs for one (instance, seed); prune arms only if the reference log allows."""
    out = {
        "nf4": RunConfig(p, i, 8, t, seed, num_full=4),
        "nf2": RunConfig(p, i, 8, t, seed, num_full=2),
    }
    ref = default(p, i, t, seed ^ 1)
    if not runs.has(ref):
        return out
    sig = pool_signals(runs.log(ref.key), t)
    idle = prune_idle(sig)
    if idle:
        m = len(idle)
        out["prune"] = RunConfig(p, i, 8, t, seed, ignore=tuple(idle))
        out["random"] = RunConfig(
            p, i, 8, t, seed, ignore=tuple(prune_random(sig, m, f"{i}/{seed}"))
        )
        out["top"] = RunConfig(p, i, 8, t, seed, ignore=tuple(prune_top(sig, m)))
    return out


def pool_share(runs: InstanceRuns, ref: RunConfig) -> float:
    return sum(
        s.late_share for s in pool_signals(runs.log(ref.key), ref.time_limit).values()
    )


def sign_p(wins: int, losses: int) -> float:
    """Two-sided exact sign test."""
    n, k = wins + losses, min(wins, losses)
    return min(1.0, 2 * sum(comb(n, j) for j in range(k + 1)) / 2**n) if n else 1.0


def summary(label: str, diffs: list[float]) -> str:
    w, lo = sum(d < -1e-9 for d in diffs), sum(d > 1e-9 for d in diffs)
    if not diffs:
        return f"{label:28s} no pairs"
    return (
        f"{label:28s} {w:3d} better / {lo:3d} worse / {len(diffs) - w - lo:2d} tie   p={sign_p(w, lo):.3f}"
        f"   mean rel dPI {mean(diffs):+.3f}  median {median(diffs):+.3f}"
    )


def report(t: float, seeds: tuple[int, ...], verbose: bool) -> None:
    rel: dict[str, list[float]] = defaultdict(list)  # (arm - default) / default PI
    by_share: dict[tuple[str, bool], list[float]] = defaultdict(list)
    for p, i in instances(t):
        runs = InstanceRuns(p, i)
        for seed in seeds:
            d = default(p, i, t, seed)
            if runs.find(d) is None:
                continue
            base = runs.primal(d).integral
            a = arms(p, i, t, seed, runs)
            pi = {
                k: runs.primal(c).integral
                for k, c in a.items()
                if runs.find(c) is not None
            }
            ref = default(p, i, t, seed ^ 1)
            share = pool_share(runs, ref) if runs.has(ref) else None
            for k, v in pi.items():
                rel[k].append((v - base) / max(base, 1e-9))
                if share is not None and k.startswith("nf"):
                    by_share[(k, share >= 0.5)].append((v - base) / max(base, 1e-9))
            if {"prune", "random"} <= pi.keys():
                rel["prune vs random"].append(
                    (pi["prune"] - pi["random"]) / max(base, 1e-9)
                )
            if {"prune", "top"} <= pi.keys():
                rel["prune vs top"].append((pi["prune"] - pi["top"]) / max(base, 1e-9))
            if verbose:
                cells = "  ".join(f"{k} {v:.2f}" for k, v in pi.items())
                print(
                    f"{p}/{i} s{seed}: default {base:.2f}  {cells}  pool share {share if share is None else round(share, 2)}"
                )
    print(
        f"\nPhase G, 8 workers, {t:.0f} s, seeds {seeds} (negative = better than the default / than the second arm)"
    )
    for k in (*ARMS, "prune vs random", "prune vs top"):
        print(summary(k, rel[k]))
    for k in ("nf4", "nf2"):
        for high in (False, True):
            print(
                summary(
                    f"{k} | pool share {'>=' if high else '<'} 0.5", by_share[(k, high)]
                )
            )


if __name__ == "__main__":
    args = sys.argv[1:]
    t = float(args[args.index("--time") + 1]) if "--time" in args else 10.0
    rest = [
        a
        for j, a in enumerate(args)
        if a not in ("--time", "--report", "-v") and (j == 0 or args[j - 1] != "--time")
    ]
    seeds = tuple(int(s) for s in rest) or (0, 1)
    if "--report" in args:
        report(t, seeds, "-v" in args)
    else:
        insts = instances(t)
        run_jobs(
            [default(p, i, t, s) for p, i in insts for s in seeds], budget=12
        )  # references first
        jobs = [
            c
            for p, i in insts
            for s in seeds
            for c in arms(p, i, t, s, InstanceRuns(p, i)).values()
        ]
        run_jobs(
            [j for j in jobs if InstanceRuns(j.problem, j.instance).find(j) is None],
            budget=12,
        )

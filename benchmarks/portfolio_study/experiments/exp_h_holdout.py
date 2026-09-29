"""Phase H: both study results re-tested on held-out instances with more seeds.

Created 2026-09-28 (fourth session). The hypotheses and the test are fixed in PLAN.md
(Phase H) before any run; this script only executes them.
    H1  ``late``: at n in {2, 3, 4, 6} workers, the top-F(n) full subsolvers by ``late`` from
        the 8-worker log beat CP-SAT's default choice on the primal integral (Phase C protocol).
    H2  LNS: at 8 workers, ``num_full_subsolvers=4`` beats the default when the LNS pool
        delivered >= 0.5 of the time-weighted improvement in the log of the partner seed
        (0<->1, 2<->3), and does not when it delivered less (Phase G protocol).
    H2b the same at 12 workers with ``num_full_subsolvers=6`` (half the workers), seeds 0, 1.
Part 2 (same night, PLAN.md "Phase H part 2"): the two reliability limits of the card.
    H3  H1 with the ranking read from a 12-worker log (the card's "many full" caveat).
    H4  H1 at 30 s: 8-worker 30 s log, n in {2, 4, 6} at 30 s (the "long run" caveat).
    H5  H2 at 30 s (nf4 vs default at 8 workers, 30 s).
Stages (each resumable, runs are cached):
    uv run python -m portfolio_study.experiments.exp_h_holdout screen     # seed 0, 8 w, 10 s
    uv run python -m portfolio_study.experiments.exp_h_holdout select     # -> holdout.json
    uv run python -m portfolio_study.experiments.exp_h_holdout base       # 8 w default, seeds 0-3
    uv run python -m portfolio_study.experiments.exp_h_holdout late       # H1 runs
    uv run python -m portfolio_study.experiments.exp_h_holdout lns        # H2 + H2b runs
    uv run python -m portfolio_study.experiments.exp_h_holdout late12     # H3 runs
    uv run python -m portfolio_study.experiments.exp_h_holdout long       # H4 + H5 runs
    uv run python -m portfolio_study.experiments.exp_h_holdout report [-v]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from portfolio_study.experiments.exp_c_verify import verify_jobs
from portfolio_study.experiments.exp_g_lns import pool_share, sign_p
from portfolio_study.study.holdout import candidates, screen_all, select
from portfolio_study.study.metrics import METRICS
from portfolio_study.study.runner import (
    DATA,
    ROOT,
    RunConfig,
    default_full_count,
    run_jobs,
)
from portfolio_study.study.signals import extract_signals
from portfolio_study.study.store import InstanceRuns

T = 10.0
SEEDS = (0, 1, 2, 3)
WORKERS = (2, 3, 4, 6)
LNS_ARMS = ((8, 4, SEEDS), (12, 6, (0, 1)))  # (workers, num_full_subsolvers, seeds)
LONG_T, LONG_WORKERS = 30.0, (2, 4, 6)
THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7)
SELECTION = Path(__file__).resolve().parents[1] / "holdout.json"


def listing() -> dict[str, list[str]]:
    sys.path.insert(0, str(ROOT))
    from bench.problems import all_problems

    return {
        p: [i.name for i in prob.instances(DATA / p)]
        for p, prob in all_problems().items()
    }


def screen_cfg(p: str, i: str) -> RunConfig:
    return RunConfig(p, i, workers=8, time_limit=T, seed=0)


def chosen() -> list[tuple[str, str]]:
    return [tuple(x) for x in json.loads(SELECTION.read_text())["selected"]]  # type: ignore[misc]


def do_select() -> None:
    pairs = candidates(listing())

    def log_of(p: str, i: str):
        runs = InstanceRuns(p, i)
        return runs.log(screen_cfg(p, i).key) if runs.has(screen_cfg(p, i)) else None

    screened = screen_all(pairs, log_of)
    sel = select(screened)
    SELECTION.write_text(json.dumps({
        "rule": "study/holdout.py: larger half per class minus Phase A; passes_screen; first 4 per class",
        "screened": [[p, i, s.passed, s.reason] for p, i, s in screened],
        "selected": sel,
    }, indent=1))  # fmt: skip
    passed = sum(s.passed for *_, s in screened)
    print(f"screened {len(screened)}, passed {passed}, selected {len(sel)} "
          f"from {len({p for p, _ in sel})} classes -> {SELECTION.name}")  # fmt: skip


def lns_pairs(
    p: str, i: str, w: int, nf: int, seed: int, t: float = T
) -> tuple[RunConfig, RunConfig, RunConfig]:
    """(default, arm, reference) for one LNS comparison."""
    return (
        RunConfig(p, i, w, t, seed),
        RunConfig(p, i, w, t, seed, num_full=nf),
        RunConfig(p, i, w, t, seed ^ 1),
    )


def summary(label: str, diffs: list[float]) -> str:
    w, lo = sum(d < -1e-9 for d in diffs), sum(d > 1e-9 for d in diffs)
    if not diffs:
        return f"{label:34s} no pairs"
    return (f"{label:34s} {w:3d} better / {lo:3d} worse / {len(diffs) - w - lo:2d} tie  p={sign_p(w, lo):.4f}"
            f"  mean {mean(diffs):+.3f}  median {median(diffs):+.3f}")  # fmt: skip


def report_late(
    insts: list[tuple[str, str]],
    verbose: bool,
    base_w: int = 8,
    t: float = T,
    workers: tuple[int, ...] = WORKERS,
    label: str = "H1",
) -> None:
    """H1/H3/H4: absolute and relative PI differences (late - default), as in Phase C."""
    by_n: dict[int, list[float]] = defaultdict(list)
    per_inst: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_cls: dict[str, list[float]] = defaultdict(list)
    rel: list[float] = []
    same = 0
    for p, i in insts:
        runs = InstanceRuns(p, i)
        for seed in SEEDS:
            base = RunConfig(p, i, base_w, t, seed)
            if not runs.has(base):
                continue
            sig = extract_signals(runs.log(base.key), t)
            by_default = sorted(sig, key=lambda k: sig[k].default_rank)
            for n in workers:
                f = default_full_count(n)
                top = tuple(METRICS["late"](sig)[:f])
                d, c = (
                    RunConfig(p, i, n, t, seed),
                    RunConfig(p, i, n, t, seed, subsolvers=top),
                )
                if set(top) == set(by_default[:f]):
                    same += 1
                    continue
                if runs.find(d) is None or runs.find(c) is None:
                    continue
                pd, pc = runs.primal(d).integral, runs.primal(c).integral
                by_n[n].append(pc - pd)
                by_cls[p].append(pc - pd)
                per_inst[(p, i)].append(pc - pd)
                rel.append((pc - pd) / max(pd, 1e-9))
                if verbose:
                    print(
                        f"  {p}/{i} s{seed} n={n}: default {pd:.3f}  late {pc:.3f}  {'+'.join(top)}"
                    )
    print(
        f"\n{label} late top-F(n) from the {base_w}-worker log vs default, {t:.0f} s, seeds {SEEDS}"
        f" ({same} pairs with the default set skipped)"
    )
    print(summary("all (abs dPI)", [x for v in by_n.values() for x in v]))
    print(summary("all (relative dPI)", rel))
    print(summary("per instance (mean abs dPI)", [mean(v) for v in per_inst.values()]))
    for n in workers:
        print(summary(f"n={n}", by_n[n]))
    for p in sorted(by_cls):
        print(summary(f"  {p}", by_cls[p]))


def report_lns(
    insts: list[tuple[str, str]], verbose: bool, arms=LNS_ARMS, t: float = T
) -> None:
    """H2/H2b/H5: relative PI difference of the nf arm, split by the reference pool share."""
    for w, nf, seeds in arms:
        rows: list[tuple[float, float, str]] = []  # (share, rel dPI, class)
        for p, i in insts:
            runs = InstanceRuns(p, i)
            for seed in seeds:
                d, a, ref = lns_pairs(p, i, w, nf, seed, t)
                if not (runs.has(d) and runs.has(a) and runs.has(ref)):
                    continue
                pd, pa = runs.primal(d).integral, runs.primal(a).integral
                share = pool_share(runs, ref)
                rows.append((share, (pa - pd) / max(pd, 1e-9), p))
                if verbose:
                    print(
                        f"  {p}/{i} s{seed} w{w}: default {pd:.3f}  nf{nf} {pa:.3f}  pool share {share:.2f}"
                    )
        print(
            f"\nH2 num_full_subsolvers={nf} vs default at {w} workers, {t:.0f} s, seeds {seeds} (relative dPI)"
        )
        print(summary("all", [r for _, r, _ in rows]))
        for th in THRESHOLDS:
            print(summary(f"pool share >= {th}", [r for s, r, _ in rows if s >= th]))
            print(summary(f"pool share <  {th}", [r for s, r, _ in rows if s < th]))
        hi = defaultdict(list)
        for s, r, p in rows:
            if s >= 0.5:
                hi[p].append(r)
        for p in sorted(hi):
            print(summary(f"  >=0.5 {p}", hi[p]))


if __name__ == "__main__":
    args = sys.argv[1:]
    stage = args[0] if args else "report"
    if stage == "screen":
        run_jobs([screen_cfg(p, i) for p, i in candidates(listing())], budget=12)
    elif stage == "select":
        do_select()
    elif stage == "base":
        run_jobs(
            [RunConfig(p, i, 8, T, s) for p, i in chosen() for s in SEEDS], budget=12
        )
    elif stage == "late":
        run_jobs(
            [
                j
                for p, i in chosen()
                for s in SEEDS
                for j in verify_jobs(p, i, s, ["late"], T, 8, WORKERS)
            ],
            budget=12,
        )
    elif stage == "lns":
        jobs = []
        for w, nf, seeds in LNS_ARMS:
            jobs += [
                c for p, i in chosen() for s in seeds for c in lns_pairs(p, i, w, nf, s)
            ]
        run_jobs(
            list({(j.problem, j.instance, j.key): j for j in jobs}.values()), budget=12
        )
    elif stage == "late12":
        insts = chosen()
        run_jobs(
            [RunConfig(p, i, 12, T, s) for p, i in insts for s in SEEDS], budget=12
        )
        jobs = [
            j
            for p, i in insts
            for s in SEEDS
            for j in verify_jobs(p, i, s, ["late"], T, 12, WORKERS)
        ]
        run_jobs(jobs, budget=12)
    elif stage == "long":
        insts = chosen()
        run_jobs(
            [RunConfig(p, i, 8, LONG_T, s) for p, i in insts for s in SEEDS], budget=12
        )
        jobs = [
            j
            for p, i in insts
            for s in SEEDS
            for j in verify_jobs(p, i, s, ["late"], LONG_T, 8, LONG_WORKERS)
        ]
        jobs += [lns_pairs(p, i, 8, 4, s, LONG_T)[1] for p, i in insts for s in SEEDS]
        run_jobs(jobs, budget=12)
    else:
        insts, v = chosen(), "-v" in args
        report_late(insts, v)
        report_lns(insts, v)
        if "--part2" in args:
            report_late(insts, v, base_w=12, label="H3")
            report_late(insts, v, t=LONG_T, workers=LONG_WORKERS, label="H4")
            report_lns(insts, v, arms=((8, 4, SEEDS),), t=LONG_T)

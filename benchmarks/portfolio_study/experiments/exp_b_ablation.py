"""Phase B: ablation ground truth for the kept instances.

For each full subsolver X of the 8-worker/10 s seed-0 run:
  leave-one-out  7 workers, subsolvers = the other five   (F(7) = 5, same thread split)
  solo           2 workers, subsolvers = [X]              (F(2) = 1, plus one LNS thread)
plus the default portfolios at 7 and 2 workers as references (shared with Phase C).
    uv run python -m portfolio_study.experiments.exp_b_ablation [--solo-only] [seed ...]
(the leave-one-out runs turned out to be within noise, see PLAN.md; --solo-only skips them)
"""

import sys

from cpsat_logutils import parse_log

from portfolio_study.study.candidates import PHASE_B
from portfolio_study.study.runner import RunConfig, run_jobs
from portfolio_study.study.signals import full_subsolver_names


def ablation_jobs(problem: str, instance: str, seeds: tuple[int, ...], time_limit: float = 10.0, solo_only: bool = False) -> list[RunConfig]:
    base = RunConfig(problem, instance, workers=8, time_limit=time_limit, seed=0)
    names = full_subsolver_names(parse_log(base.log_path.read_text()))
    jobs: list[RunConfig] = []
    for seed in seeds:
        jobs.append(RunConfig(problem, instance, workers=2, time_limit=time_limit, seed=seed))
        if not solo_only:
            jobs.append(RunConfig(problem, instance, workers=7, time_limit=time_limit, seed=seed))
        for x in names:
            others = tuple(n for n in names if n != x)
            jobs.append(RunConfig(problem, instance, workers=2, time_limit=time_limit, seed=seed, subsolvers=(x,)))
            if not solo_only:
                jobs.append(RunConfig(problem, instance, workers=7, time_limit=time_limit, seed=seed, subsolvers=others))
    return jobs


if __name__ == "__main__":
    args = sys.argv[1:]
    solo_only = "--solo-only" in args
    seeds = tuple(int(s) for s in args if s != "--solo-only") or (0,)
    jobs = [j for p, i in PHASE_B for j in ablation_jobs(p, i, seeds, solo_only=solo_only)]
    run_jobs(jobs, budget=12)

"""Phase A: baseline 8-worker runs at 10 s, two seeds, for every screening candidate.

Purpose: (1) see which instances have an active objective search in the first 10 s,
(2) estimate run-to-run noise, (3) produce the 'normal run' logs the metrics read.
    uv run python -m portfolio_study.experiments.exp_a_screen
"""

from portfolio_study.study.candidates import PHASE_A
from portfolio_study.study.runner import RunConfig, run_jobs

if __name__ == "__main__":
    jobs = [RunConfig(p, i, workers=8, time_limit=10, seed=s) for p, i in PHASE_A for s in (0, 1)]
    run_jobs(jobs, budget=12)

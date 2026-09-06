"""Produce the pair of example logs that show what a solution hint does.

Created 2026-09 for the analyzer's hint card: none of the 295 corpus logs passes a
hint, so the "was my hint used?" analysis had no example to look at. The script
solves the same random job-shop instance twice with the same limit -- once plain,
once with every variable hinted to its value from the first run -- and writes both
logs to ``example_logs/``:

    uv run python make_hint_example.py

The instance is generated here (fixed seed) instead of downloaded, so the logs stay
reproducible and nothing copyrighted is involved. Re-run it only when the logs
should be refreshed for a new OR-Tools version; the descriptions in
``knowledge/examples.toml`` mention the numbers, so update them together.
"""

from __future__ import annotations

import random
from pathlib import Path

from ortools.sat.python import cp_model

OUT = Path(__file__).resolve().parents[1] / "example_logs"
JOBS, MACHINES, SEED = 15, 15, 20260906
TIME_LIMIT, WORKERS = 10.0, 8


def instance() -> list[list[tuple[int, int]]]:
    """``jobs[j] = [(machine, duration), ...]``: a Taillard-style random job-shop."""
    rng = random.Random(SEED)
    jobs = []
    for _ in range(JOBS):
        order = list(range(MACHINES))
        rng.shuffle(order)
        jobs.append([(machine, rng.randint(1, 99)) for machine in order])
    return jobs


def build(jobs: list[list[tuple[int, int]]]) -> tuple[cp_model.CpModel, list[cp_model.IntVar]]:
    """Standard disjunctive model; also returns every variable, for hinting."""
    horizon = sum(duration for job in jobs for _, duration in job)
    model = cp_model.CpModel()
    starts: dict[tuple[int, int], cp_model.IntVar] = {}
    ends: dict[tuple[int, int], cp_model.IntVar] = {}
    machine_intervals: dict[int, list] = {m: [] for m in range(MACHINES)}
    for j, job in enumerate(jobs):
        for t, (machine, duration) in enumerate(job):
            start = model.new_int_var(0, horizon, f"s_{j}_{t}")
            end = model.new_int_var(0, horizon, f"e_{j}_{t}")
            starts[j, t], ends[j, t] = start, end
            machine_intervals[machine].append(
                model.new_interval_var(start, duration, end, f"i_{j}_{t}")
            )
            if t:
                model.add(start >= ends[j, t - 1])
    for intervals in machine_intervals.values():
        model.add_no_overlap(intervals)
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, [ends[j, len(job) - 1] for j, job in enumerate(jobs)])
    model.minimize(makespan)
    variables = [*starts.values(), *ends.values(), makespan]
    assert len(model.proto.variables) == len(variables), "unexpected auxiliary variables"
    return model, variables


def solve(model: cp_model.CpModel, out: Path) -> tuple[cp_model.CpSolver, int]:
    solver = cp_model.CpSolver()
    p = solver.parameters
    p.max_time_in_seconds = TIME_LIMIT
    p.num_workers = WORKERS
    p.log_search_progress = True
    p.log_to_stdout = False
    p.log_subsolver_statistics = True
    lines: list[str] = []
    solver.log_callback = lines.append
    status = solver.solve(model)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out.name}: {solver.status_name(status)} objective={solver.objective_value:.0f}")
    return solver, status


def main() -> None:
    jobs = instance()
    model, variables = build(jobs)
    solver, _ = solve(model, OUT / "915_jobshop_no_hint.txt")

    values = [solver.value(v) for v in variables]
    # A second, identical model: hinting the solved one would reuse its solution pool.
    hinted_model, hinted_variables = build(jobs)
    for variable, value in zip(hinted_variables, values, strict=True):
        hinted_model.add_hint(variable, value)
    solve(hinted_model, OUT / "915_jobshop_hinted.txt")


if __name__ == "__main__":
    main()

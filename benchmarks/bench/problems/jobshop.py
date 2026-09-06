"""Classic job-shop scheduling (JSP), minimizing makespan.

Created 2026-09-06 as base data for the CP-SAT log analyzer: JSP logs are the
prototypical *scheduling* log (no-overlap propagation, long objective-bound
plateaus, ``sched_lb``/``sched_ub`` subsolvers in the log).

Instance source: JSPLIB, <https://github.com/tamy0612/JSPLIB> (raw files under
``instances/``; a curated union of the classic OR-Library sets ft/la/abz/orb/
swv/yn/ta). Format: ``#``-comment lines, then ``<jobs> <machines>``, then one
line per job with ``<machine> <duration>`` pairs in processing order; every job
visits every machine exactly once. Parsing is token based, so line breaks
inside a job do not matter.

Model: one interval per operation (with per-operation time windows tightened by
the durations before/after it inside its job), ``add_no_overlap`` per machine,
``start >= end`` of the previous operation of the same job, and a makespan
variable pinned with ``add_max_equality`` to the job end times.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://raw.githubusercontent.com/tamy0612/JSPLIB/master/instances"

# Curated, roughly easy -> hard (size and published CP-SAT/CP difficulty).
INSTANCE_NAMES = [
    "ft06",  # 6x6
    "la01",  # 10x5
    "la02",
    "la06",  # 15x5
    "la11",  # 20x5
    "ft20",  # 20x5
    "la16",  # 10x10
    "ft10",  # 10x10 (mt10)
    "orb01",
    "orb05",
    "abz5",
    "abz6",
    "la21",  # 15x10
    "la26",  # 20x10
    "la31",  # 30x10
    "la36",  # 15x15
    "la40",
    "abz7",  # 20x15
    "abz9",
    "swv01",  # 20x10
    "swv06",  # 20x15
    "swv11",  # 50x10
    "ta01",  # 15x15
    "yn1",  # 20x20
    "ta21",  # 20x20
    "ta41",  # 30x20
    "ta61",  # 50x20
]

Job = list[tuple[int, int]]  # (machine, duration) in processing order


def download(data_dir: Path) -> None:
    """Fetch the chosen JSPLIB instance files (a few hundred kB in total)."""
    for name in INSTANCE_NAMES:
        fetch(f"{BASE_URL}/{name}", data_dir / f"{name}.txt")


def instances(data_dir: Path) -> list[Instance]:
    out: list[Instance] = []
    for name in INSTANCE_NAMES:
        path = data_dir / f"{name}.txt"
        if not path.exists():
            continue
        jobs = parse(path)
        out.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "jobs": len(jobs),
                    "machines": len({m for job in jobs for m, _ in job}),
                    "operations": sum(len(job) for job in jobs),
                    "total_duration": sum(d for job in jobs for _, d in job),
                },
            )
        )
    return out


def parse(path: Path) -> list[Job]:
    """Read a JSPLIB instance into a list of jobs of ``(machine, duration)``."""
    tokens: list[int] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tokens.extend(int(float(t)) for t in line.split())
    if len(tokens) < 2:
        raise ValueError(f"{path}: no data found")
    num_jobs, num_machines = tokens[0], tokens[1]
    values = tokens[2 : 2 + 2 * num_jobs * num_machines]
    if len(values) != 2 * num_jobs * num_machines:
        raise ValueError(f"{path}: expected {2 * num_jobs * num_machines} values, got {len(values)}")
    jobs: list[Job] = []
    pos = 0
    for _ in range(num_jobs):
        job: Job = []
        for _ in range(num_machines):
            job.append((values[pos], values[pos + 1]))
            pos += 2
        jobs.append(job)
    return jobs


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    jobs = parse(instance.path)
    horizon = sum(d for job in jobs for _, d in job)

    model = cp_model.CpModel()
    machine_intervals: dict[int, list[cp_model.IntervalVar]] = defaultdict(list)
    job_ends: list[cp_model.IntVar] = []

    for j, job in enumerate(jobs):
        # Tight time windows: an operation cannot start before its predecessors
        # in the job are done, nor end later than the remaining work allows.
        head = 0  # duration of the operations before the current one
        tail = sum(d for _, d in job)
        previous_end: cp_model.IntVar | None = None
        for t, (machine, duration) in enumerate(job):
            tail -= duration
            start = model.new_int_var(head, horizon - duration - tail, f"s_{j}_{t}")
            end = model.new_int_var(head + duration, horizon - tail, f"e_{j}_{t}")
            interval = model.new_interval_var(start, duration, end, f"op_{j}_{t}")
            machine_intervals[machine].append(interval)
            if previous_end is not None:
                model.add(start >= previous_end)
            previous_end = end
            head += duration
        assert previous_end is not None
        job_ends.append(previous_end)

    for intervals in machine_intervals.values():
        model.add_no_overlap(intervals)

    lower_bound = max(
        max(sum(d for _, d in job) for job in jobs),
        max(
            sum(d for job in jobs for m, d in job if m == machine)
            for machine in machine_intervals
        ),
    )
    makespan = model.new_int_var(lower_bound, horizon, "makespan")
    model.add_max_equality(makespan, job_ends)
    model.minimize(makespan)
    return model


PROBLEM = Problem(
    name="jobshop",
    description="Classic job-shop scheduling (makespan) from JSPLIB",
    download=download,
    instances=instances,
    build=build,
    source="https://github.com/tamy0612/JSPLIB",
)

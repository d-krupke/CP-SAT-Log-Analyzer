"""Flexible job-shop scheduling (FJSP), minimizing makespan.

Created 2026-09-06 as base data for the CP-SAT log analyzer. Compared to the
plain job shop this adds an *assignment* decision on top of the sequencing one,
so the logs show optional-interval/no-overlap propagation together with a much
larger Boolean part (useful to see how the log looks when both SAT and
scheduling propagators are busy).

Instance source: <https://github.com/SchedulingLab/fjsp-instances> (raw files
under ``brandimarte/`` and ``hurink/{edata,rdata,vdata}/``), which collects the
Brandimarte (1993) ``mk*`` set and the Hurink et al. (1994) multi-purpose
machine variants of the OR-Library job-shop instances.

Format (from that repository's README): first line ``<jobs> <machines>``, then
one line per job: ``<#operations>`` followed, per operation, by
``<#eligible machines>`` and that many ``<machine> <duration>`` pairs. Machine
indices are 0-based. Parsing is token based (line breaks are irrelevant).

Model: one ``(start, end)`` pair per operation plus one *optional* interval per
eligible machine that reuses those very variables, so the chosen mode is the
only one that fixes ``end == start + duration``; ``add_exactly_one`` over the
presence literals selects the machine, ``add_no_overlap`` per machine enforces
machine capacity, precedences chain the operations of a job, and the makespan
is pinned to the job end times with ``add_max_equality``.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://raw.githubusercontent.com/SchedulingLab/fjsp-instances/master"

# name -> path inside the repository; ordered roughly easy -> hard.
INSTANCE_FILES: dict[str, str] = {
    "mk01": "brandimarte/mk01.txt",
    "mk02": "brandimarte/mk02.txt",
    "edata_la02": "hurink/edata/la02.txt",
    "rdata_la02": "hurink/rdata/la02.txt",
    "vdata_la02": "hurink/vdata/la02.txt",
    "mk08": "brandimarte/mk08.txt",
    "mk03": "brandimarte/mk03.txt",
    "mk04": "brandimarte/mk04.txt",
    "mk05": "brandimarte/mk05.txt",
    "edata_la21": "hurink/edata/la21.txt",
    "vdata_la21": "hurink/vdata/la21.txt",
    "rdata_la21": "hurink/rdata/la21.txt",
    "mk09": "brandimarte/mk09.txt",
    "mk07": "brandimarte/mk07.txt",
    "edata_la36": "hurink/edata/la36.txt",
    "vdata_abz7": "hurink/vdata/abz7.txt",
    "mk10": "brandimarte/mk10.txt",
    "mk06": "brandimarte/mk06.txt",
}

Mode = tuple[int, int]  # (machine, duration)
Operation = list[Mode]
Job = list[Operation]


def download(data_dir: Path) -> None:
    """Fetch the chosen FJSP instance files (a few hundred kB in total)."""
    for name, rel in INSTANCE_FILES.items():
        fetch(f"{BASE_URL}/{rel}", data_dir / f"{name}.txt")


def instances(data_dir: Path) -> list[Instance]:
    out: list[Instance] = []
    for name in INSTANCE_FILES:
        path = data_dir / f"{name}.txt"
        if not path.exists():
            continue
        jobs, num_machines = parse(path)
        operations = sum(len(job) for job in jobs)
        modes = sum(len(op) for job in jobs for op in job)
        out.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "jobs": len(jobs),
                    "machines": num_machines,
                    "operations": operations,
                    "modes": modes,
                    "flexibility": round(modes / operations, 2),
                },
            )
        )
    return out


def parse(path: Path) -> tuple[list[Job], int]:
    """Read an FJSP instance into ``(jobs, num_machines)``."""
    tokens = [
        int(float(t))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        for t in line.split()
    ]
    if len(tokens) < 2:
        raise ValueError(f"{path}: no data found")
    num_jobs, num_machines = tokens[0], tokens[1]
    pos = 2
    jobs: list[Job] = []
    for _ in range(num_jobs):
        num_operations = tokens[pos]
        pos += 1
        job: Job = []
        for _ in range(num_operations):
            num_modes = tokens[pos]
            pos += 1
            operation: Operation = []
            for _ in range(num_modes):
                operation.append((tokens[pos], tokens[pos + 1]))
                pos += 2
            if not operation:
                raise ValueError(f"{path}: operation without eligible machine")
            job.append(operation)
        jobs.append(job)
    observed = max(m for job in jobs for op in job for m, _ in op) + 1
    return jobs, max(num_machines, observed)


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    jobs, _ = parse(instance.path)
    # A purely sequential schedule with the slowest machine per operation is
    # always feasible, so its length is a valid horizon.
    horizon = sum(max(d for _, d in op) for job in jobs for op in job)

    model = cp_model.CpModel()
    machine_intervals: dict[int, list[cp_model.IntervalVar]] = defaultdict(list)
    job_ends: list[cp_model.IntVar] = []

    for j, job in enumerate(jobs):
        min_durations = [min(d for _, d in op) for op in job]
        head = 0  # shortest possible work before the current operation
        tail = sum(min_durations)
        previous_end: cp_model.IntVar | None = None
        for t, operation in enumerate(job):
            shortest = min_durations[t]
            tail -= shortest
            start = model.new_int_var(head, horizon - tail - shortest, f"s_{j}_{t}")
            end = model.new_int_var(head + shortest, horizon - tail, f"e_{j}_{t}")
            presences = []
            for machine, duration in operation:
                presence = model.new_bool_var(f"x_{j}_{t}_m{machine}")
                # Sharing start/end across the modes keeps the model small: the
                # size equation of an absent optional interval is not enforced.
                machine_intervals[machine].append(
                    model.new_optional_interval_var(
                        start, duration, end, presence, f"op_{j}_{t}_m{machine}"
                    )
                )
                presences.append(presence)
            model.add_exactly_one(presences)
            if previous_end is not None:
                model.add(start >= previous_end)
            previous_end = end
            head += shortest
        assert previous_end is not None
        job_ends.append(previous_end)

    for intervals in machine_intervals.values():
        model.add_no_overlap(intervals)

    lower_bound = max(sum(min(d for _, d in op) for op in job) for job in jobs)
    makespan = model.new_int_var(lower_bound, horizon, "makespan")
    model.add_max_equality(makespan, job_ends)
    model.minimize(makespan)
    return model


PROBLEM = Problem(
    name="flexible_jobshop",
    description="Flexible job shop (Brandimarte/Hurink), makespan",
    download=download,
    instances=instances,
    build=build,
    source="https://github.com/SchedulingLab/fjsp-instances",
)

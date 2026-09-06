"""Resource-constrained project scheduling (RCPSP) from PSPLIB, makespan.

Created 2026-09-06 as base data for the CP-SAT log analyzer. RCPSP logs are the
cumulative-resource counterpart to the job-shop logs: few variables but strong
scheduling propagation, so they show energetic reasoning, long plateaus of the
objective bound and (for j120) the typical "good primal, weak dual" picture.

Instance source: PSPLIB, <https://www.om-db.wi.tum.de/psplib/> — the single-mode
sets j30/j60/j120 are served as zip archives by
``download_dataset.php?set=<set>&mode=sm&format=zip`` (~0.5-1.3 MB each; the old
``files/<set>.sm.zip`` links are gone). Only the selected ``.sm`` members are
extracted; the archives are kept so ``download`` stays cheap on re-runs.

Format (``.sm``): ``***``-separated sections. The header gives the number of
jobs (including super-source and sink), the horizon and the number of renewable
resources; ``PRECEDENCE RELATIONS`` lists ``jobnr #modes #successors succ...``;
``REQUESTS/DURATIONS`` lists ``jobnr mode duration demand_1 ... demand_R``;
``RESOURCEAVAILABILITIES`` gives one capacity per renewable resource.

Model: one interval per activity with time windows from the critical-path
forward/backward pass, ``start[successor] >= end[activity]`` per precedence,
one ``add_cumulative`` per renewable resource over the activities that actually
demand it, and a makespan variable pinned with ``add_max_equality``.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

SET_URL = "https://www.om-db.wi.tum.de/psplib/download_dataset.php?set={set}&mode=sm&format=zip"

# 8 instances per set, spread over the parameter grid (network complexity /
# resource factor / resource strength); j30 is easy, j120 is mostly open.
SELECTION: dict[str, list[str]] = {
    "j30": ["j301_1", "j307_1", "j3013_1", "j3021_5", "j3029_3", "j3037_1", "j3043_5", "j3048_1"],
    "j60": ["j601_1", "j607_1", "j6013_1", "j6021_5", "j6029_3", "j6037_1", "j6043_5", "j6048_1"],
    "j120": [
        "j1201_1",
        "j1209_1",
        "j12017_1",
        "j12025_5",
        "j12033_3",
        "j12041_1",
        "j12053_5",
        "j12060_1",
    ],
}


@dataclass(frozen=True)
class Project:
    """One RCPSP instance; activity 0 is the super-source, ``n-1`` the sink."""

    durations: list[int]
    successors: list[list[int]]  # 0-based
    demands: list[list[int]]  # [activity][resource]
    capacities: list[int]

    @property
    def num_activities(self) -> int:
        return len(self.durations)

    @property
    def num_resources(self) -> int:
        return len(self.capacities)


def download(data_dir: Path) -> None:
    """Fetch the three archives and extract the selected ``.sm`` members."""
    for set_name, names in SELECTION.items():
        missing = [n for n in names if not (data_dir / f"{n}.sm").exists()]
        if not missing:
            continue
        archive = fetch(SET_URL.format(set=set_name), data_dir / f"{set_name}.sm.zip")
        with zipfile.ZipFile(archive) as zf:
            members = {m.lower(): m for m in zf.namelist()}
            for name in missing:
                member = members.get(f"{name}.sm")
                if member is None:
                    raise ValueError(f"{archive}: {name}.sm not in archive")
                (data_dir / f"{name}.sm").write_bytes(zf.read(member))


def instances(data_dir: Path) -> list[Instance]:
    """All selected instances, sorted by size and then by resource pressure."""
    found: list[tuple[tuple[int, float], Instance]] = []
    for set_name, names in SELECTION.items():
        for name in names:
            path = data_dir / f"{name}.sm"
            if not path.exists():
                continue
            project = parse(path)
            critical_path = _critical_path_length(project)
            pressure = _resource_pressure(project, critical_path)
            found.append(
                (
                    (project.num_activities, pressure),
                    Instance(
                        name=name,
                        path=path,
                        meta={
                            "set": set_name,
                            "activities": project.num_activities,
                            "resources": project.num_resources,
                            "precedences": sum(len(s) for s in project.successors),
                            "critical_path": critical_path,
                            "resource_pressure": round(pressure, 3),
                        },
                    ),
                )
            )
    return [inst for _, inst in sorted(found, key=lambda item: item[0])]


def parse(path: Path) -> Project:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    num_activities = 0
    num_resources = 0
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("jobs (incl"):
            num_activities = int(line.split(":")[1])
        elif stripped.startswith("- renewable"):
            num_resources = int(line.split(":")[1].split()[0])
    if num_activities <= 0 or num_resources <= 0:
        raise ValueError(f"{path}: could not read header (jobs/renewable resources)")

    precedence_rows = _rows_after(lines, "PRECEDENCE RELATIONS")
    request_rows = _rows_after(lines, "REQUESTS/DURATIONS")
    capacity_rows = _rows_after(lines, "RESOURCEAVAILABILITIES")
    if len(precedence_rows) != num_activities or len(request_rows) != num_activities:
        raise ValueError(f"{path}: expected {num_activities} rows per section")
    if not capacity_rows or len(capacity_rows[0]) != num_resources:
        raise ValueError(f"{path}: expected {num_resources} resource capacities")

    successors = [[s - 1 for s in row[3:]] for row in precedence_rows]
    durations = [row[2] for row in request_rows]
    demands = [row[3 : 3 + num_resources] for row in request_rows]
    if any(row[1] != 1 for row in request_rows):
        raise ValueError(f"{path}: multi-mode instance, expected single mode (.sm)")
    return Project(durations, successors, demands, capacity_rows[0])


def _rows_after(lines: list[str], header: str) -> list[list[int]]:
    """Numeric rows of the ``***``-terminated section introduced by ``header``."""
    try:
        start = next(i for i, line in enumerate(lines) if line.strip().startswith(header))
    except StopIteration:
        raise ValueError(f"section {header!r} not found") from None
    rows: list[list[int]] = []
    for line in lines[start + 1 :]:
        if line.startswith("***"):
            break
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        rows.append([int(p) for p in parts])
    return rows


def _critical_path_length(project: Project) -> int:
    """Longest path through the precedence graph, ignoring resources."""
    earliest = _earliest_starts(project)
    return max(earliest[a] + project.durations[a] for a in range(project.num_activities))


def _earliest_starts(project: Project) -> list[int]:
    earliest = [0] * project.num_activities
    for activity in _topological_order(project):
        finish = earliest[activity] + project.durations[activity]
        for successor in project.successors[activity]:
            earliest[successor] = max(earliest[successor], finish)
    return earliest


def _latest_finishes(project: Project, horizon: int) -> list[int]:
    latest = [horizon] * project.num_activities
    for activity in reversed(_topological_order(project)):
        for successor in project.successors[activity]:
            latest[activity] = min(latest[activity], latest[successor] - project.durations[successor])
    return latest


def _topological_order(project: Project) -> list[int]:
    indegree = [0] * project.num_activities
    for succs in project.successors:
        for successor in succs:
            indegree[successor] += 1
    queue = [a for a, deg in enumerate(indegree) if deg == 0]
    order: list[int] = []
    while queue:
        activity = queue.pop()
        order.append(activity)
        for successor in project.successors[activity]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(order) != project.num_activities:
        raise ValueError("precedence graph contains a cycle")
    return order


def _resource_pressure(project: Project, critical_path: int) -> float:
    """Mean resource utilization if the project ran in critical-path time."""
    if critical_path <= 0:
        return 0.0
    total = 0.0
    for resource, capacity in enumerate(project.capacities):
        work = sum(project.durations[a] * project.demands[a][resource] for a in range(project.num_activities))
        total += work / (capacity * critical_path)
    return total / project.num_resources


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    project = parse(instance.path)
    horizon = sum(project.durations)
    earliest = _earliest_starts(project)
    latest = _latest_finishes(project, horizon)

    model = cp_model.CpModel()
    starts: list[cp_model.IntVar] = []
    ends: list[cp_model.IntVar] = []
    intervals: list[cp_model.IntervalVar] = []
    for activity in range(project.num_activities):
        duration = project.durations[activity]
        start = model.new_int_var(earliest[activity], latest[activity] - duration, f"s{activity}")
        end = model.new_int_var(earliest[activity] + duration, latest[activity], f"e{activity}")
        starts.append(start)
        ends.append(end)
        intervals.append(model.new_interval_var(start, duration, end, f"a{activity}"))

    for activity, successors in enumerate(project.successors):
        for successor in successors:
            model.add(starts[successor] >= ends[activity])

    for resource, capacity in enumerate(project.capacities):
        using = [
            a
            for a in range(project.num_activities)
            if project.demands[a][resource] > 0 and project.durations[a] > 0
        ]
        if using:
            model.add_cumulative(
                [intervals[a] for a in using],
                [project.demands[a][resource] for a in using],
                capacity,
            )

    makespan = model.new_int_var(_critical_path_length(project), horizon, "makespan")
    model.add_max_equality(makespan, ends)
    model.minimize(makespan)
    return model


PROBLEM = Problem(
    name="rcpsp",
    description="Resource-constrained project scheduling (PSPLIB j30/j60/j120)",
    download=download,
    instances=instances,
    build=build,
    source="https://www.om-db.wi.tum.de/psplib/",
)

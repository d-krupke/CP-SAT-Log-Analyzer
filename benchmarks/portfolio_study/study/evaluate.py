"""Primal performance measures of one run and paired comparisons between runs.

Created 2026-09-27 for the portfolio-importance study. Pure functions over the parsed
log (``cpsat_logutils``): the objective trajectory, the primal gap against a best-known
value, its integral over the run, and helpers to compare two runs on the same instance.
"""

from __future__ import annotations

from dataclasses import dataclass

from cpsat_logutils import CpSatLog


def trajectory(log: CpSatLog) -> list[tuple[float, float]]:
    """(time, objective) of every improving solution, in log order."""
    if not log.search:
        return []
    return [(e.time, e.objective) for e in log.search.events if e.solution_index is not None and e.objective is not None]


def sense(log: CpSatLog) -> int:
    """+1 for minimization, -1 for maximization."""
    s = log.search.objective_sense if log.search else None
    return -1 if s == "maximize" else 1


@dataclass(frozen=True)
class Primal:
    final: float | None  # final objective (None = no solution)
    final_gap: float  # (final - best)/max(|best|,1), 1.0 when no solution
    integral: float  # integral of the gap over [0, T]
    first_time: float | None  # time of the first solution
    n_solutions: int


def primal(log: CpSatLog, best_known: float, time_limit: float) -> Primal:
    traj = trajectory(log)
    sgn = sense(log)
    scale = max(abs(best_known), 1.0)

    def gap(z: float) -> float:
        return max(sgn * (z - best_known) / scale, 0.0)

    if not traj:
        return Primal(None, 1.0, time_limit, None, 0)
    integral, t_prev, g_prev = 0.0, 0.0, 1.0
    for t, z in traj:
        t = min(t, time_limit)
        integral += (t - t_prev) * g_prev
        t_prev, g_prev = t, min(gap(z), 1.0)
    integral += (time_limit - t_prev) * g_prev
    return Primal(traj[-1][1], gap(traj[-1][1]), integral, traj[0][0], len(traj))


def better_of(a: float, b: float, eps: float = 1e-9) -> int:
    """-1 if a is smaller (better), +1 if b is, 0 if equal within eps."""
    if a < b - eps:
        return -1
    if b < a - eps:
        return 1
    return 0

"""Derived analysis of a parsed log: overview metrics, plot data and insights.

The parser (``cpsatlog``) only structures the log; this module interprets it
for the UI. Everything here carries the line numbers it was derived from so the
frontend can highlight the evidence. Insights are heuristics grounded in the
CP-SAT primer (search_core.md); keep them conservative and explain the evidence.
"""

from __future__ import annotations

from typing import Any

from cpsatlog import CpSatLog
from cpsatlog.schema import Loc, SearchEvent
from pydantic import BaseModel, Field

from .explanations import describe_subsolver
from .parameters import ParameterInfo, describe_all

OLDEST_WELL_SUPPORTED = (9, 8)


class Metric(BaseModel):
    key: str
    label: str
    value: str
    line: int | None = None
    hint: str | None = None
    level: str = "info"  # info | good | warn | bad


class SeriesPoint(BaseModel):
    time: float
    value: float
    line: int
    subsolver: str | None = None


class ProgressSeries(BaseModel):
    objective_sense: str | None
    solutions: list[SeriesPoint]
    bounds: list[SeriesPoint]
    done_time: float | None = None
    done_line: int | None = None


class SubsolverContribution(BaseModel):
    name: str
    solutions: int = 0
    bounds: int = 0
    first_solution_time: float | None = None
    best_solution_line: int | None = None
    description: str | None = None


class Insight(BaseModel):
    level: str  # info | good | warn | bad
    title: str
    text: str
    lines: list[int] = Field(default_factory=list)


class Analysis(BaseModel):
    metrics: list[Metric]
    progress: ProgressSeries
    parameters: list[ParameterInfo]
    subsolvers: list[SubsolverContribution]
    insights: list[Insight]


def analyze(log: CpSatLog) -> Analysis:
    progress = build_progress(log)
    return Analysis(
        metrics=build_metrics(log),
        progress=progress,
        parameters=describe_all(_parameters(log)),
        subsolvers=build_subsolvers(log),
        insights=build_insights(log, progress),
    )


def _parameters(log: CpSatLog) -> dict[str, Any]:
    if log.solver and log.solver.parameters:
        return dict(log.solver.parameters.value)
    return {}


def _fmt(x: float | int | None, digits: int = 4) -> str:
    if x is None:
        return "?"
    if isinstance(x, int):
        return f"{x:,}"
    if abs(x) >= 1e15 or x != x:
        return str(x)
    if x == int(x) and abs(x) < 1e12:
        return f"{int(x):,}"
    return f"{x:,.{digits}g}" if abs(x) < 1 else f"{x:,.{max(digits, 2)}f}".rstrip("0").rstrip(".")


def _loc_val[T](loc: Loc[T] | None) -> T | None:
    return loc.value if loc is not None else None


def build_metrics(log: CpSatLog) -> list[Metric]:
    metrics: list[Metric] = []
    solver, response = log.solver, log.response
    if solver and solver.version:
        old = (
            solver.version_tuple is not None
            and tuple(solver.version_tuple[:2]) < OLDEST_WELL_SUPPORTED
        )
        metrics.append(
            Metric(
                key="version",
                label="OR-Tools",
                value=solver.version.value,
                line=solver.version.line,
                level="warn" if old else "info",
                hint=(
                    "Old version: the log format differs and many newer improvements are missing. "
                    "Consider upgrading OR-Tools."
                    if old
                    else None
                ),
            )
        )
    workers = _num_workers(log)
    if workers is not None:
        metrics.append(
            Metric(
                key="workers",
                label="Workers",
                value=str(workers.value),
                line=workers.line,
                level="warn" if workers.value < 8 else "info",
                hint=(
                    "With fewer than 8 workers only part of the portfolio runs (1 worker = "
                    "default_lp only)."
                    if workers.value < 8
                    else None
                ),
            )
        )
    if response:
        if response.status:
            status = response.status.value
            level = {"OPTIMAL": "good", "FEASIBLE": "warn", "INFEASIBLE": "info"}.get(status, "bad")
            metrics.append(
                Metric(
                    key="status",
                    label="Status",
                    value=status,
                    line=response.status.line,
                    level=level,
                )
            )
        if response.objective:
            metrics.append(
                Metric(
                    key="objective",
                    label="Objective",
                    value=_fmt(response.objective.value),
                    line=response.objective.line,
                )
            )
        if response.best_bound:
            metrics.append(
                Metric(
                    key="bound",
                    label="Best bound",
                    value=_fmt(response.best_bound.value),
                    line=response.best_bound.line,
                )
            )
        gap = response.gap
        if gap is not None:
            metrics.append(
                Metric(
                    key="gap",
                    label="Gap",
                    value=f"{gap:.2f}%",
                    line=response.best_bound.line if response.best_bound else None,
                    level="good" if gap < 1e-6 else ("warn" if gap < 10 else "bad"),
                    hint="|objective - bound| / max(1, |objective|)",
                )
            )
        if response.walltime:
            metrics.append(
                Metric(
                    key="walltime",
                    label="Wall time",
                    value=f"{response.walltime.value:.2f} s",
                    line=response.walltime.line,
                )
            )
    presolve_time = _presolve_duration(log)
    if presolve_time is not None:
        walltime = _loc_val(response.walltime) if response else None
        share = presolve_time / walltime if walltime else None
        metrics.append(
            Metric(
                key="presolve_time",
                label="Presolve",
                value=f"{presolve_time:.2f} s"
                + (f" ({share * 100:.0f}%)" if share is not None else ""),
                line=log.presolve.span.start if log.presolve else None,
                level="warn" if share is not None and share > 0.5 else "info",
                hint="Time from the start of presolve to the start of the search."
                if share is None or share <= 0.5
                else "Presolve dominates the run time.",
            )
        )
    for model, key, label in (
        (log.initial_model, "initial_model", "Initial model"),
        (log.presolved_model, "presolved_model", "Presolved model"),
    ):
        if model and model.num_variables:
            metrics.append(
                Metric(
                    key=key,
                    label=label,
                    value=(
                        f"{model.num_variables.value:,} vars, {model.num_constraints:,} constraints"
                    ),
                    line=model.span.start,
                )
            )
    if log.presolve_summary and log.presolve_summary.closed_by_presolve:
        metrics.append(
            Metric(
                key="closed_by_presolve",
                label="Closed by presolve",
                value="yes",
                line=log.presolve_summary.closed_by_presolve.line,
                level="good",
            )
        )
    if log.search:
        sols = log.search.events_of_kind("solution")
        bounds = log.search.events_of_kind("bound")
        metrics.append(
            Metric(
                key="solutions",
                label="Solutions",
                value=str(len(sols)),
                line=sols[-1].line if sols else log.search.span.start,
                hint="Improving solutions reported in the search log.",
            )
        )
        metrics.append(
            Metric(
                key="bound_events",
                label="Bound updates",
                value=str(len(bounds)),
                line=bounds[-1].line if bounds else log.search.span.start,
                hint="Logged bound improvements (throttled by the solver).",
            )
        )
        if sols:
            metrics.append(
                Metric(
                    key="first_solution",
                    label="First solution",
                    value=f"{sols[0].time:.2f} s",
                    line=sols[0].line,
                )
            )
            metrics.append(
                Metric(
                    key="last_solution",
                    label="Last improvement",
                    value=f"{sols[-1].time:.2f} s",
                    line=sols[-1].line,
                )
            )
    return metrics


def _presolve_duration(log: CpSatLog) -> float | None:
    """Presolve start -> search start; falls back to the sum of the step times.

    The step times overlap (nested passes, parallel probing), so their sum can
    exceed the wall time and is only a rough fallback.
    """
    if log.presolve is None:
        return None
    if log.presolve.start_time is not None and log.search is not None and log.search.start:
        return max(0.0, log.search.start.time - log.presolve.start_time.value)
    if log.presolve.total_step_time:
        return log.presolve.total_step_time
    return None


def _num_workers(log: CpSatLog) -> Loc[int] | None:
    if log.solver is None:
        return None
    if log.solver.num_workers is not None:
        return log.solver.num_workers
    params = log.solver.parameters
    if params:
        for key in ("num_workers", "num_search_workers"):
            val = params.value.get(key)
            if isinstance(val, int) and val > 0:
                return Loc(value=val, line=params.line)
    if log.search and log.search.start and log.search.start.num_workers:
        return Loc(value=log.search.start.num_workers, line=log.search.start.line)
    return None


def build_progress(log: CpSatLog) -> ProgressSeries:
    sense = log.search.objective_sense if log.search else None
    solutions: list[SeriesPoint] = []
    bounds: list[SeriesPoint] = []
    done_time = done_line = None
    if log.search is None:
        return ProgressSeries(objective_sense=sense, solutions=[], bounds=[])
    for ev in log.search.events:
        if ev.time is None:
            continue
        if ev.kind == "solution" and ev.objective is not None:
            solutions.append(
                SeriesPoint(time=ev.time, value=ev.objective, line=ev.line, subsolver=ev.subsolver)
            )
        b = _bound_of(ev, sense)
        if b is not None and ev.kind in ("solution", "bound"):
            bounds.append(SeriesPoint(time=ev.time, value=b, line=ev.line, subsolver=ev.subsolver))
        if ev.kind == "done":
            done_time, done_line = ev.time, ev.line
    return ProgressSeries(
        objective_sense=sense,
        solutions=solutions,
        bounds=bounds,
        done_time=done_time,
        done_line=done_line,
    )


def _bound_of(ev: SearchEvent, sense: str | None) -> float | None:
    if sense == "maximize":
        return ev.next_ub
    if sense == "minimize":
        return ev.next_lb
    return None


def build_subsolvers(log: CpSatLog) -> list[SubsolverContribution]:
    contributions: dict[str, SubsolverContribution] = {}

    def get(name: str) -> SubsolverContribution:
        if name not in contributions:
            contributions[name] = SubsolverContribution(
                name=name, description=describe_subsolver(name)
            )
        return contributions[name]

    if log.search:
        for ev in log.search.events:
            if not ev.subsolver:
                continue
            c = get(ev.subsolver)
            if ev.kind == "solution":
                c.solutions += 1
                c.best_solution_line = ev.line
                if c.first_solution_time is None:
                    c.first_solution_time = ev.time
            elif ev.kind == "bound":
                c.bounds += 1
    for table, attr in ((log.stats.solutions, "solutions"), (log.stats.objective_bounds, "bounds")):
        if table is None:
            continue
        for row in table.rows:
            num = row.values.get("Num")
            if isinstance(num, int):
                setattr(get(row.name), attr, max(getattr(get(row.name), attr), num))
    return sorted(contributions.values(), key=lambda c: (-c.solutions, -c.bounds, c.name))


def build_insights(log: CpSatLog, progress: ProgressSeries) -> list[Insight]:
    out: list[Insight] = []
    response = log.response
    status = _loc_val(response.status) if response else None

    if log.presolve_summary and log.presolve_summary.closed_by_presolve:
        out.append(
            Insight(
                level="good",
                title="Solved by presolve",
                text=(
                    "Presolve alone settled the model; no search was needed. The search "
                    "statistics are therefore empty."
                ),
                lines=[log.presolve_summary.closed_by_presolve.line],
            )
        )
    if status == "FEASIBLE" and response and response.gap is not None:
        out.append(
            Insight(
                level="warn",
                title="Not proven optimal",
                text=(
                    f"The solver stopped with a gap of {response.gap:.2f}%. Either the "
                    f"incumbent is not optimal or the "
                    "bound could not be raised. Check whether solutions or bounds stalled "
                    "last (progress plot) to decide "
                    "between more time, better hints/LNS, or a stronger formulation for the "
                    "relaxation."
                ),
                lines=[response.status.line] if response.status else [],
            )
        )
    if status == "UNKNOWN":
        out.append(
            Insight(
                level="bad",
                title="No solution found",
                text=(
                    "The solver found no feasible solution within the limits. Try a hint, a "
                    "longer time limit, or check the model for very tight constraints."
                ),
                lines=[response.status.line] if response and response.status else [],
            )
        )
    if status == "INFEASIBLE":
        out.append(
            Insight(
                level="info",
                title="Model proven infeasible",
                text=(
                    "Infeasibility was proven. Check the presolve log: often a fixed variable or "
                    "a domain that presolve emptied reveals the conflicting constraints."
                ),
                lines=[response.status.line] if response and response.status else [],
            )
        )
    _insight_stalls(log, progress, status, out)
    _insight_search_stats(log, out)
    _insight_response_counters(log, out)
    _insight_lns(log, out)
    _insight_model_growth(log, out)
    return out


def _insight_stalls(
    log: CpSatLog, progress: ProgressSeries, status: str | None, out: list[Insight]
) -> None:
    if status != "FEASIBLE" or not log.response or not log.response.walltime:
        return
    wall = log.response.walltime.value
    if progress.solutions:
        last = progress.solutions[-1]
        if wall > 0 and last.time < 0.5 * wall:
            out.append(
                Insight(
                    level="info",
                    title="Solutions stalled early",
                    text=(
                        f"The last improving solution was found at {last.time:.1f}s of "
                        f"{wall:.1f}s. The remaining time went "
                        "into (unsuccessful) proving. If the bound also stalled, the solution "
                        "may well be optimal but hard to prove."
                    ),
                    lines=[last.line],
                )
            )
    if progress.bounds:
        last_b = progress.bounds[-1]
        if wall > 0 and last_b.time < 0.5 * wall:
            out.append(
                Insight(
                    level="info",
                    title="Bound stalled early",
                    text=(
                        f"The proven bound last improved at {last_b.time:.1f}s. Weak "
                        f"relaxations are typical for big-M "
                        "formulations; tighter constraints or redundant constraints for the "
                        "LP can help."
                    ),
                    lines=[last_b.line],
                )
            )


def _insight_search_stats(log: CpSatLog, out: list[Insight]) -> None:
    table = log.stats.search_stats
    if table is None:
        return
    rows = [(r, r.values.get("Conflicts"), r.values.get("Branches")) for r in table.rows]
    rows = [
        (r, c, b) for r, c, b in rows if isinstance(c, int | float) and isinstance(b, int | float)
    ]
    if not rows:
        return
    best = max(rows, key=lambda t: t[1])
    r, conflicts, branches = best
    if branches and conflicts / branches > 0.5:
        out.append(
            Insight(
                level="info",
                title="Conflict-heavy search",
                text=(
                    f"Worker `{r.name}` had {int(conflicts):,} conflicts for {int(branches):,} "
                    f"branches: it learned from "
                    "most decisions, a sign of a tightly constrained combinatorial core."
                ),
                lines=[r.line],
            )
        )
    elif branches and conflicts / branches < 0.05:
        out.append(
            Insight(
                level="info",
                title="Mostly feasible descent",
                text=(
                    f"Worker `{r.name}` had only {int(conflicts):,} conflicts for "
                    f"{int(branches):,} branches: the search "
                    "descends feasibly most of the time; difficulty lies in the optimisation, "
                    "not feasibility."
                ),
                lines=[r.line],
            )
        )


def _insight_response_counters(log: CpSatLog, out: list[Insight]) -> None:
    response, table = log.response, log.stats.search_stats
    if response is None or response.conflicts is None or table is None:
        return
    conflicts = [r.values.get("Conflicts") for r in table.rows]
    max_conf = max((c for c in conflicts if isinstance(c, int | float)), default=None)
    if max_conf is not None and max_conf > 0 and response.conflicts.value < 0.1 * max_conf:
        out.append(
            Insight(
                level="info",
                title="Summary counters are per worker",
                text=(
                    f"The summary reports {response.conflicts.value:,} conflicts while the "
                    f"busiest worker had "
                    f"{int(max_conf):,}. The summary counters come from the worker that "
                    f"returned the solution, not from "
                    "the whole portfolio. Use the Search stats table to judge the effort."
                ),
                lines=[response.conflicts.line],
            )
        )


def _insight_lns(log: CpSatLog, out: list[Insight]) -> None:
    table = log.stats.lns_stats
    if table is None:
        return
    high = []
    for r in table.rows:
        closed = r.values.get("Closed")
        if isinstance(closed, int | float) and closed > 80:
            high.append(r)
    if len(high) >= max(3, len(table.rows) // 2):
        out.append(
            Insight(
                level="info",
                title="LNS neighbourhoods closed quickly",
                text=(
                    "Most LNS neighbourhoods were solved to completion; the sub-problems are "
                    "easy, so the difficulty "
                    "is raised adaptively. Consider whether the solutions came mostly from "
                    "LNS (Solutions table) or "
                    "from the exact workers."
                ),
                lines=[r.line for r in high[:3]],
            )
        )


def _insight_model_growth(log: CpSatLog, out: list[Insight]) -> None:
    a, b = log.initial_model, log.presolved_model
    if not (a and b and a.num_variables and b.num_variables):
        return
    va, vb = a.num_variables.value, b.num_variables.value
    if vb > 2 * va and vb > 1000:
        out.append(
            Insight(
                level="info",
                title="Presolve expanded the model",
                text=(
                    f"The presolved model has {vb:,} variables versus {va:,} initially. "
                    f"Presolve expanded high-level "
                    "constraints (e.g. AllDifferent, element, tables) into Booleans the "
                    "propagators understand; this is "
                    "normal but shows where the search effort goes."
                ),
                lines=[b.span.start],
            )
        )
    elif va and vb < 0.5 * va:
        out.append(
            Insight(
                level="good",
                title="Presolve shrank the model",
                text=f"Presolve reduced the model from {va:,} to {vb:,} variables.",
                lines=[b.span.start],
            )
        )

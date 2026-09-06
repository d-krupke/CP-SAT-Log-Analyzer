"""Derived analysis of a parsed log: the ``Analysis`` model, plot data and subsolver roles.

The parser (``cpsatlog``) only structures the log; the ``app`` modules interpret
it for the UI. Everything carries the line numbers it was derived from so the
frontend can highlight the evidence. Overview tiles live in ``metrics.py``,
insights in ``insights.py``, the solution hint in ``hints.py``; their texts and
thresholds in ``v2/knowledge/``.
"""

from __future__ import annotations

import math
from typing import Any

from cpsatlog import CpSatLog
from cpsatlog.schema import SearchEvent
from pydantic import BaseModel, Field

from .explanations import describe_subsolver
from .hints import HintReport, build_hint_report
from .insights import Insight, build_insights
from .metrics import Metric, build_metrics, loc_val
from .parameters import ParameterInfo, describe_all


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
    end_time: float | None = Field(
        default=None, description="Wall time of the run (response) or the #Done time"
    )


class SubsolverContribution(BaseModel):
    name: str
    solutions: int = 0
    bounds: int = 0
    first_solution_time: float | None = None
    best_solution_line: int | None = None
    description: str | None = Field(default=None, description="One-line summary of the worker")
    role: str | None = None


class Analysis(BaseModel):
    metrics: list[Metric]
    progress: ProgressSeries
    parameters: list[ParameterInfo]
    subsolvers: list[SubsolverContribution]
    insights: list[Insight]
    hint: HintReport


def analyze(log: CpSatLog) -> Analysis:
    progress = build_progress(log)
    hint = build_hint_report(log)
    return Analysis(
        metrics=build_metrics(log),
        progress=progress,
        parameters=describe_all(_parameters(log)),
        subsolvers=build_subsolvers(log),
        insights=build_insights(log, progress, hint),
        hint=hint,
    )


def _parameters(log: CpSatLog) -> dict[str, Any]:
    if log.solver and log.solver.parameters:
        return dict(log.solver.parameters.value)
    return {}


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
    end_time = loc_val(log.response.walltime) if log.response else done_time
    _append_final_bound(log, bounds, done_time or end_time)
    return ProgressSeries(
        objective_sense=sense,
        solutions=solutions,
        bounds=bounds,
        done_time=done_time,
        end_time=end_time,
        done_line=done_line,
    )


def _append_final_bound(log: CpSatLog, bounds: list[SeriesPoint], at: float | None) -> None:
    """Add the response's ``best_bound`` as the last bound point.

    The search log often stops printing bound lines before the search ends (e.g. the
    optimality proof is only reflected in the response), so without this the bound
    curve would end at a stale value.
    """
    if log.search is None or log.search.objective_sense is None:
        return  # satisfaction problem: the response prints a meaningless 0 bound
    if log.response is None or log.response.best_bound is None or at is None:
        return
    value = log.response.best_bound.value
    if not math.isfinite(value) or (bounds and bounds[-1].value == value):
        return
    bounds.append(SeriesPoint(time=at, value=value, line=log.response.best_bound.line))


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
            doc = describe_subsolver(name)
            contributions[name] = SubsolverContribution(
                name=name,
                description=doc.summary if doc else None,
                role=doc.role if doc else None,
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

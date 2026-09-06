"""Insights: heuristic observations shown in the Overview card.

Split out of ``analysis.py`` when the knowledge base moved to TOML. Each rule
here decides *whether* an insight fires and which log lines are its evidence;
the thresholds, levels, titles and texts come from
``v2/knowledge/insights.toml`` (rule key = TOML section). Keep the rules
conservative and grounded in the CP-SAT primer (search_core.md).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cpsatlog import CpSatLog
from pydantic import BaseModel, Field

from .knowledge import load

if TYPE_CHECKING:
    from .analysis import ProgressSeries


class Insight(BaseModel):
    level: str  # info | good | warn | bad
    title: str
    text: str
    lines: list[int] = Field(default_factory=list)


def _rule(key: str) -> dict[str, Any]:
    return load("insights")[key]


def _insight(key: str, lines: list[int], **fields: Any) -> Insight:
    rule = _rule(key)
    return Insight(
        level=rule["level"],
        title=rule["title"],
        text=rule["text"].format(**fields),
        lines=lines,
    )


def build_insights(log: CpSatLog, progress: ProgressSeries) -> list[Insight]:
    out: list[Insight] = []
    response = log.response
    status = response.status.value if response and response.status else None
    status_lines = [response.status.line] if response and response.status else []

    if log.presolve_summary and log.presolve_summary.closed_by_presolve:
        out.append(_insight("solved_by_presolve", [log.presolve_summary.closed_by_presolve.line]))
    if status == "FEASIBLE" and response and response.gap is not None:
        out.append(_insight("not_proven_optimal", status_lines, gap=response.gap))
    if status == "UNKNOWN":
        out.append(_insight("no_solution", status_lines))
    if status == "INFEASIBLE":
        out.append(_insight("infeasible", status_lines))
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
    if wall <= 0:
        return
    if progress.solutions:
        last = progress.solutions[-1]
        if last.time < _rule("solutions_stalled")["fraction_of_walltime"] * wall:
            out.append(_insight("solutions_stalled", [last.line], last_time=last.time, wall=wall))
    if progress.bounds:
        last_b = progress.bounds[-1]
        if last_b.time < _rule("bound_stalled")["fraction_of_walltime"] * wall:
            out.append(_insight("bound_stalled", [last_b.line], last_time=last_b.time, wall=wall))


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
    r, conflicts, branches = max(rows, key=lambda t: t[1])
    if not branches:
        return
    ratio = conflicts / branches
    fields = {"worker": r.name, "conflicts": int(conflicts), "branches": int(branches)}
    if ratio > _rule("conflict_heavy")["min_ratio"]:
        out.append(_insight("conflict_heavy", [r.line], **fields))
    elif ratio < _rule("feasible_descent")["max_ratio"]:
        out.append(_insight("feasible_descent", [r.line], **fields))


def _insight_response_counters(log: CpSatLog, out: list[Insight]) -> None:
    response, table = log.response, log.stats.search_stats
    if response is None or response.conflicts is None or table is None:
        return
    conflicts = [r.values.get("Conflicts") for r in table.rows]
    max_conf = max((c for c in conflicts if isinstance(c, int | float)), default=None)
    if max_conf is None or max_conf <= 0:
        return
    if response.conflicts.value < _rule("per_worker_counters")["max_ratio"] * max_conf:
        out.append(
            _insight(
                "per_worker_counters",
                [response.conflicts.line],
                response_conflicts=response.conflicts.value,
                max_conflicts=int(max_conf),
            )
        )


def _insight_lns(log: CpSatLog, out: list[Insight]) -> None:
    table = log.stats.lns_stats
    if table is None:
        return
    rule = _rule("lns_closed_quickly")
    high = []
    for r in table.rows:
        closed = _percent(r.values.get("Closed"))
        if closed is not None and closed > rule["closed_percent"]:
            high.append(r)
    if len(high) >= max(rule["min_rows"], len(table.rows) // 2):
        out.append(
            _insight(
                "lns_closed_quickly",
                [r.line for r in high[:3]],
                count=len(high),
                total=len(table.rows),
            )
        )


def _percent(cell: Any) -> float | None:
    """Value of a percentage cell such as ``50%``.

    The LNS stats table prints `Closed` with a percent sign, so the parser keeps it as text;
    without this the rule silently never fired (found while mining the benchmark corpus).
    """
    if isinstance(cell, int | float):
        return float(cell)
    if isinstance(cell, str):
        try:
            return float(cell.removesuffix("%"))
        except ValueError:
            return None
    return None


def _insight_model_growth(log: CpSatLog, out: list[Insight]) -> None:
    a, b = log.initial_model, log.presolved_model
    if not (a and b and a.num_variables and b.num_variables):
        return
    va, vb = a.num_variables.value, b.num_variables.value
    grow = _rule("presolve_expanded")
    if vb > grow["growth_factor"] * va and vb > grow["min_variables"]:
        out.append(_insight("presolve_expanded", [b.span.start], initial=va, presolved=vb))
    elif va and vb < _rule("presolve_shrank")["shrink_factor"] * va:
        out.append(_insight("presolve_shrank", [b.span.start], initial=va, presolved=vb))

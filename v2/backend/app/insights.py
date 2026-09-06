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
    _insight_log_quality(log, out)
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
    _insight_objective_removed(log, out)
    return out


def _insight_log_quality(log: CpSatLog, out: list[Insight]) -> None:
    """State what is wrong with the log itself before interpreting its numbers.

    Users paste logs that were killed mid-run, cut off at the top, mixed with their own
    prints, or are not CP-SAT logs at all. Everything derived from such a log is partial, so
    it must be said first; the unrecognised lines are also highlighted in the raw log view.
    """
    looks_like_cpsat = bool(log.solver or log.initial_model or log.response or log.search)
    unparsed_lines = sum(len(block.lines) for block in log.unparsed)
    if not looks_like_cpsat:
        if unparsed_lines:
            out.append(_insight("not_a_cpsat_log", [log.unparsed[0].span.start]))
        return
    if log.response is None:
        last = log.blocks[-1].span.end if log.blocks else log.num_lines
        out.append(_insight("log_truncated", [last], last_line=last))
    if log.solver is None:
        first = log.blocks[0].span.start if log.blocks else 1
        out.append(_insight("head_missing", [first]))
    if unparsed_lines >= _rule("unrecognised_lines")["min_lines"]:
        out.append(
            _insight(
                "unrecognised_lines",
                [block.span.start for block in log.unparsed[:3]],
                count=unparsed_lines,
                places=len(log.unparsed),
                first_line=log.unparsed[0].span.start,
            )
        )


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


def _objective_terms(model: Any) -> int:
    """Objective variables the model line reports (`(#bools: 80 in objective)`)."""
    total = 0
    for field in (model.num_bools_in_objective, model.num_ints_in_objective):
        if field is not None:
            total += field.value
    return total


def _insight_objective_removed(log: CpSatLog, out: list[Insight]) -> None:
    """Presolve pinned the objective to a constant: the presolved line has no objective terms.

    Seen on six benchmark logs (bin packing, 2D bin packing, graph colouring, dominating set).
    It is worth pointing out because the portfolio silently changes shape: the objective-based
    workers and every LNS neighbourhood are dropped.
    """
    a, b = log.initial_model, log.presolved_model
    if not (a and b):
        return
    terms = _objective_terms(a)
    if terms and not _objective_terms(b):
        out.append(_insight("objective_removed_by_presolve", [b.span.start], terms=terms))


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

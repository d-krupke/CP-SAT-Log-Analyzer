"""Overview tiles (metrics) derived from a parsed log.

Split out of ``analysis.py`` when the knowledge base moved to TOML: the
thresholds and hint texts come from ``v2/knowledge/metrics.toml``; this module
computes the values and anchors each tile to the log line it came from.
"""

from __future__ import annotations

from cpsatlog import CpSatLog
from cpsatlog.schema import Loc
from pydantic import BaseModel

from .hints import HintReport
from .knowledge import load


class Metric(BaseModel):
    key: str
    label: str
    value: str
    line: int | None = None
    hint: str | None = None
    level: str = "info"  # info | good | warn | bad


def fmt(x: float | int | None, digits: int = 4) -> str:
    if x is None:
        return "?"
    if isinstance(x, int):
        return f"{x:,}"
    if abs(x) >= 1e15 or x != x:
        return str(x)
    if x == int(x) and abs(x) < 1e12:
        return f"{int(x):,}"
    return f"{x:,.{digits}g}" if abs(x) < 1 else f"{x:,.{max(digits, 2)}f}".rstrip("0").rstrip(".")


def loc_val[T](loc: Loc[T] | None) -> T | None:
    return loc.value if loc is not None else None


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split(".") if p.isdigit())


# Value and level of the Hint tile, keyed as in metrics.toml: the statuses of
# hints.HintStatus plus `used` for a hint the solver actually started from.
_HINT_TILE: dict[str, tuple[str, str]] = {
    "none": ("none", "info"),
    "vacuous": ("none", "info"),
    "used": ("used", "good"),
    "accepted": ("accepted", "good"),
    "infeasible": ("infeasible", "warn"),
    "incomplete": ("incomplete", "info"),
    "outside_domain": ("outside domain", "warn"),
    "breaks_assumptions": ("breaks assumptions", "warn"),
    "ignored": ("ignored", "warn"),
    "debug_only": ("debug only", "info"),
    "other": ("given", "info"),
}


def build_metrics(log: CpSatLog, hint: HintReport) -> list[Metric]:
    cfg = load("metrics")
    metrics: list[Metric] = []
    solver, response = log.solver, log.response
    if solver and solver.version:
        old = solver.version_tuple is not None and tuple(solver.version_tuple[:2]) < (
            _version_tuple(cfg["version"]["oldest_well_supported"])
        )
        metrics.append(
            Metric(
                key="version",
                label="OR-Tools",
                value=solver.version.value,
                line=solver.version.line,
                level="warn" if old else "info",
                hint=cfg["version"]["hint_old"] if old else None,
            )
        )
    workers = _num_workers(log)
    if workers is not None:
        few = workers.value < cfg["workers"]["min_for_full_portfolio"]
        metrics.append(
            Metric(
                key="workers",
                label="Workers",
                value=str(workers.value),
                line=workers.line,
                level="warn" if few else "info",
                hint=cfg["workers"]["hint_few"] if few else None,
            )
        )
    if log.initial_model or log.response or log.search or hint.has_evidence:
        metrics.append(_hint_metric(hint, cfg))
    if response:
        metrics.extend(_response_metrics(log, cfg))
    presolve_time = _presolve_duration(log)
    if presolve_time is not None:
        walltime = loc_val(response.walltime) if response else None
        share = presolve_time / walltime if walltime else None
        dominates = share is not None and share > cfg["presolve_time"]["warn_share"]
        metrics.append(
            Metric(
                key="presolve_time",
                label="Presolve",
                value=f"{presolve_time:.2f} s"
                + (f" ({share * 100:.0f}%)" if share is not None else ""),
                line=log.presolve.span.start if log.presolve else None,
                level="warn" if dominates else "info",
                hint=cfg["presolve_time"]["hint_dominates" if dominates else "hint"],
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
                        f"{model.num_variables.value:,} vars\n{model.num_constraints:,} constraints"
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
        metrics.extend(_search_metrics(log, cfg))
    return metrics


def _hint_metric(hint: HintReport, cfg: dict) -> Metric:
    """Was a solution hint given, and what became of it? Shown even when there was none.

    The absence of a hint is information too - it is the cheapest thing to try on a model
    whose first solution comes late - so the tile states it instead of staying silent.
    """
    key = "used" if hint.status == "accepted" and hint.used_as_first_solution else hint.status
    value, level = _HINT_TILE[key]
    if hint.status == "incomplete" and hint.hinted is not None and hint.active is not None:
        value += f"\n{hint.hinted:,} of {hint.active:,} vars"
    elif hint.objective is not None:
        # What the hint was worth: the number to compare with the final objective.
        value += f"\nobjective {fmt(hint.objective)}"
    return Metric(
        key="hint",
        label="Hint",
        value=value,
        line=hint.lines[0] if hint.lines else None,
        level=level,
        hint=cfg["hint"][key],
    )


def _response_metrics(log: CpSatLog, cfg: dict) -> list[Metric]:
    response = log.response
    assert response is not None
    out: list[Metric] = []
    if response.status:
        status = response.status.value
        level = {"OPTIMAL": "good", "FEASIBLE": "warn", "INFEASIBLE": "info"}.get(status, "bad")
        out.append(
            Metric(
                key="status", label="Status", value=status, line=response.status.line, level=level
            )
        )
    if response.objective:
        out.append(
            Metric(
                key="objective",
                label="Objective",
                value=fmt(response.objective.value),
                line=response.objective.line,
            )
        )
    if response.best_bound:
        out.append(
            Metric(
                key="bound",
                label="Best bound",
                value=fmt(response.best_bound.value),
                line=response.best_bound.line,
            )
        )
    gap = response.gap
    if gap is not None:
        warn_below = cfg["gap"]["warn_below_percent"]
        out.append(
            Metric(
                key="gap",
                label="Gap",
                value=f"{gap:.2f}%",
                line=response.best_bound.line if response.best_bound else None,
                level="good" if gap < 1e-6 else ("warn" if gap < warn_below else "bad"),
                hint=cfg["gap"]["hint"],
            )
        )
    if response.walltime:
        out.append(
            Metric(
                key="walltime",
                label="Wall time",
                value=f"{response.walltime.value:.2f} s",
                line=response.walltime.line,
            )
        )
    return out


def _search_metrics(log: CpSatLog, cfg: dict) -> list[Metric]:
    assert log.search is not None
    sols = log.search.events_of_kind("solution")
    bounds = log.search.events_of_kind("bound")
    out = [
        Metric(
            key="solutions",
            label="Solutions",
            value=str(len(sols)),
            line=sols[-1].line if sols else log.search.span.start,
            hint=cfg["solutions"]["hint"],
        ),
        Metric(
            key="bound_events",
            label="Bound updates",
            value=str(len(bounds)),
            line=bounds[-1].line if bounds else log.search.span.start,
            hint=cfg["bound_events"]["hint"],
        ),
    ]
    if sols:
        out.append(
            Metric(
                key="first_solution",
                label="First solution",
                value=f"{sols[0].time:.2f} s",
                line=sols[0].line,
            )
        )
        out.append(
            Metric(
                key="last_solution",
                label="Last improvement",
                value=f"{sols[-1].time:.2f} s",
                line=sols[-1].line,
            )
        )
    return out


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

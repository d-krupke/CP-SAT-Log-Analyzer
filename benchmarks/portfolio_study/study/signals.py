"""Per-subsolver signals extracted from one parsed CP-SAT log.

Created 2026-09-27 for the portfolio-importance study. Everything here is pure: a
``CpSatLog`` (from ``cpsat_logutils``) goes in, a ``dict[name, SubsolverSignals]`` for
the *full-problem* subsolvers comes out. The metrics in ``metrics.py`` only see this.

Improvement accounting: the ``#k`` events carry the new best objective and the subsolver
that found it. ``improvement_share`` attributes (previous best - new best) to the finder,
normalized by (first objective - final objective) so the shares of all finders (including
LNS/LS workers) sum to 1. ``late_share`` weights each improvement by t/T, so an improvement
at the very end counts fully and one at the start not at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from cpsat_logutils import CpSatLog

from .runner import ABBREV

DEFAULT_ORDER = list(ABBREV)  # cp_model_search.cc order (max_lp_sym shares max_lp's slot)


@dataclass
class SubsolverSignals:
    name: str
    default_rank: int = 99  # position in CP-SAT's default order (0 = first)
    n_solutions: int = 0  # 'Solutions' table Num (all solutions it produced)
    first_rank: int | None = None  # 'Solutions' table Rank low end: index of its earliest solution (0 = #1)
    last_rank: int | None = None  # Rank high end: index of its latest solution (n-1 = the final best)
    last_rank_share: float = 0.0  # last_rank / (number of solutions - 1); 1.0 = it found the final solution
    n_improvements: int = 0  # '#k' events attributed to it
    improvement_share: float = 0.0  # share of the total objective improvement
    late_share: float = 0.0  # improvement share weighted by t/T
    n_late_improvements: int = 0  # '#k' events after T/3
    last_improvement_time: float = 0.0
    found_first: bool = False  # it found #1
    found_best: bool = False  # it found the final best solution (last '#k')
    n_bounds: int = 0  # 'Objective bounds' table: lower-bound improvements it produced
    shared_bounds: int = 0  # 'Improving bounds shared' Num (variable bounds it exported)
    conflicts: int = 0
    branches: int = 0
    restarts: int = 0
    wall_time: float = 0.0  # 'Task timing' total wall time
    done: bool = False  # it finished the search (#Done)
    extra: dict[str, float] = field(default_factory=dict)

    def as_row(self) -> dict[str, float | str | None]:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "extra"}


def full_subsolver_names(log: CpSatLog) -> list[str]:
    if not log.search:
        return []
    for g in log.search.subsolvers:
        if g.category == "full":
            return [e.name for e in g.subsolvers]
    return []


def _table_values(table, column: str) -> dict[str, object]:
    if table is None:
        return {}
    return {r.name: r.values.get(column) for r in table.rows}


def _rank_bounds(value) -> tuple[int, int] | None:
    """'[lo,hi]' -> (lo, hi); the ranks are chronological indices of the solutions."""
    if not isinstance(value, str) or not value.startswith("["):
        return None
    try:
        lo, hi = value.strip("[]").split(",")
        return int(lo), int(hi)
    except ValueError:
        return None


def extract_signals(log: CpSatLog, time_limit: float | None = None) -> dict[str, SubsolverSignals]:
    """Signals for every full-problem subsolver of the run (names as CP-SAT prints them)."""
    names = full_subsolver_names(log)
    sig = {n: SubsolverSignals(name=n) for n in names}
    for n in names:
        base = n.replace("max_lp_sym", "max_lp")
        sig[n].default_rank = DEFAULT_ORDER.index(base) if base in DEFAULT_ORDER else 99

    st = log.stats
    for n, v in _table_values(st.solutions, "Num").items():
        if n in sig and isinstance(v, int):
            sig[n].n_solutions = v
    total_solutions = st.solutions.count if st.solutions and st.solutions.count else None
    for n, v in _table_values(st.solutions, "Rank").items():
        bounds = _rank_bounds(v)
        if n in sig and bounds:
            sig[n].first_rank, sig[n].last_rank = bounds
            if total_solutions and total_solutions > 1:
                sig[n].last_rank_share = bounds[1] / (total_solutions - 1)
    for n, v in _table_values(st.objective_bounds, "Num").items():
        if n in sig and isinstance(v, int):
            sig[n].n_bounds = v
    for n, v in _table_values(st.improving_bounds_shared, "Num").items():
        if n in sig and isinstance(v, int):
            sig[n].shared_bounds = v
    for col, attr in (("Conflicts", "conflicts"), ("Branches", "branches"), ("Restarts", "restarts")):
        for n, v in _table_values(st.search_stats, col).items():
            if n in sig and isinstance(v, int):
                setattr(sig[n], attr, v)
    if st.task_timing:
        for r in st.task_timing.rows:
            if r.name in sig:
                sig[r.name].wall_time = r.wall.total

    events = log.search.events if log.search else []
    sols = [(e, float(e.objective)) for e in events if e.solution_index is not None and e.objective is not None]
    T = time_limit or (log.response.walltime.value if log.response and log.response.walltime else None) or 1.0
    if sols:
        total = abs(sols[0][1] - sols[-1][1])
        prev: float | None = None
        for e, obj in sols:
            who = e.subsolver or ""
            if e.solution_index == 1 and who in sig:
                sig[who].found_first = True
            if prev is not None and total > 0 and who in sig:
                delta = abs(prev - obj) / total
                sig[who].improvement_share += delta
                sig[who].late_share += delta * min(e.time / T, 1.0)
            if who in sig:
                sig[who].n_improvements += 1
                sig[who].last_improvement_time = max(sig[who].last_improvement_time, e.time)
                if e.time > T / 3:
                    sig[who].n_late_improvements += 1
            prev = obj
        last_finder = sols[-1][0].subsolver
        if last_finder in sig:
            sig[last_finder].found_best = True
    for e in events:
        if e.label == "#Done" and e.subsolver in sig:
            sig[e.subsolver].done = True
    return sig

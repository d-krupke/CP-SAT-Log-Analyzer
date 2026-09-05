"""Explain the parameters a user overrode (the ``Parameters:`` line).

Documentation comes from ``data/sat_parameters.json`` (generated from
OR-Tools' ``sat_parameters.proto`` by ``tools/extract_sat_parameters.py``).
``ADVICE`` adds curated guidance for the parameters users touch most often,
including warnings for settings that frequently hurt the overall portfolio.
"""

from __future__ import annotations

import fnmatch
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DATA_FILE = Path(__file__).parent / "data" / "sat_parameters.json"

# Parameters that are perfectly fine to set and need no warning.
SAFE = {
    "max_time_in_seconds",
    "log_search_progress",
    "log_to_stdout",
    "log_to_response",
    "num_workers",
    "num_search_workers",
    "relative_gap_limit",
    "absolute_gap_limit",
    "random_seed",
    "max_deterministic_time",
    "enumerate_all_solutions",
    "fill_tightened_domains_in_response",
    "fill_additional_solutions_in_response",
    "solution_pool_size",
    "name",
    "keep_all_feasible_solutions_in_presolve",
    "stop_after_first_solution",
    "max_number_of_conflicts",
    "max_memory_in_mb",
}

ADVICE: dict[str, str] = {
    "num_workers": (
        "Number of parallel workers. With 1 worker only `default_lp` runs; from 2 on the "
        "interleaved LNS/first-solution heuristics join, and the full portfolio (core, no_lp, "
        "max_lp, quick_restart, bound-focused workers, ...) needs 8-16+. Matching the number of "
        "*physical* cores often beats hyper-threads."
    ),
    "num_search_workers": (
        "Deprecated alias of `num_workers`; still honoured when `num_workers` is 0."
    ),
    "max_time_in_seconds": (
        "Wall-clock limit. On hitting it the status is FEASIBLE (or UNKNOWN) and the gap in the "
        "response tells you how far the solution may be from optimal."
    ),
    "relative_gap_limit": (
        "Stop once |objective - bound| / max(1, |objective|) drops below this value. The log "
        "then prints `Relative gap limit of X reached.`"
    ),
    "absolute_gap_limit": (
        "Stop once the absolute difference between objective and bound is below this."
    ),
    "search_branching": (
        "Controls the decision heuristic of the workers. `FIXED_SEARCH` forces your "
        "`add_decision_strategy` order on *every* worker and disables CP-SAT's learned "
        "heuristics, which is almost always slower unless the strategy encodes real insight; "
        "`PORTFOLIO_SEARCH`/`AUTOMATIC_SEARCH` keep the diversity of the portfolio."
    ),
    "linearization_level": (
        "0 = no LP relaxation (like `no_lp`), 1 = only linear constraints/objective (default), "
        "2 = also linearise other constraints (like `max_lp`). Setting it at the top level "
        "changes *all* workers and removes the LP diversity of the portfolio."
    ),
    "cp_model_presolve": (
        "Disabling presolve keeps the model as is. Only worth it for tiny models or when presolve "
        "time dominates a fast search; it usually hurts."
    ),
    "max_presolve_iterations": "Caps the presolve fix-point loop; lower it if presolve dominates.",
    "cp_model_probing_level": (
        "0 disables probing in presolve; probing is powerful but can be slow."
    ),
    "symmetry_level": (
        "0 disables symmetry detection/breaking. Symmetric models (identical machines, bins, "
        "vehicles) profit a lot from the default."
    ),
    "subsolvers": (
        "Replaces the default full-problem portfolio with the listed configurations. Dropping "
        "workers removes diversity; only do this based on the Solutions/Objective bounds tables."
    ),
    "extra_subsolvers": "Adds configurations (e.g. your own `subsolver_params`) to the portfolio.",
    "ignore_subsolvers": "Removes configurations from the portfolio by glob pattern.",
    "subsolver_params": (
        "Named parameter overrides for individual workers. This is the safe way to try expensive "
        "propagation settings: only that worker pays for them."
    ),
    "use_lns_only": (
        "Runs only the LNS/first-solution heuristics; needs a time limit and never proves "
        "optimality."
    ),
    "use_lns": "Disabling LNS removes the main improvement heuristics of the portfolio.",
    "use_feasibility_jump": (
        "Feasibility jump is the main first-solution heuristic; disabling it delays first "
        "solutions."
    ),
    "interleave_search": "Runs the workers interleaved in one thread (deterministic).",
    "random_seed": "Changes the random choices; run several seeds to judge variance.",
    "enumerate_all_solutions": (
        "Enumerates all solutions with a single worker and disabled presolve reductions that "
        "would drop solutions; much slower than optimisation."
    ),
    "fix_variables_to_their_hinted_value": (
        "Fixes hinted variables; useful to test if a hint is feasible."
    ),
    "keep_all_feasible_solutions_in_presolve": (
        "Prevents presolve from removing equivalent solutions (hints stay feasible) at a cost."
    ),
    "debug_crash_on_bad_hint": (
        "Crashes if the hint cannot be completed; unreliable, prefer "
        "fix_variables_to_their_hinted_value."
    ),
    "stop_after_first_solution": "Stops at the first feasible solution.",
    "max_deterministic_time": (
        "Hardware-independent limit; results are reproducible across machines."
    ),
    "share_objective_bounds": "Disabling stops workers from exchanging objective bounds.",
    "share_level_zero_bounds": "Disabling stops workers from exchanging variable bounds.",
    "share_binary_clauses": "Disabling stops workers from exchanging learned binary clauses.",
    "optimize_with_core": "Forces core-based optimisation on the default worker.",
    "use_absl_random": "Uses a non-deterministic random generator.",
    "log_search_progress": "Enables this log.",
    "log_to_stdout": "Whether the log also goes to stdout (besides the log callback).",
}

EXPENSIVE_PROPAGATION = (
    "use_*_in_no_overlap_2d",
    "use_energetic_reasoning*",
    "use_timetable_edge_finding*",
    "use_overload_checker*",
    "use_pairwise_reasoning*",
    "max_pairs_pairwise_reasoning*",
    "use_dual_scheduling_heuristics",
    "use_hard_precedences_in_cumulative",
    "exploit_all_precedences",
)


class ParameterInfo(BaseModel):
    name: str
    value: Any
    known: bool
    type: str | None = None
    default: str | None = None
    section: str | None = None
    doc: str = ""
    enum_values: dict[str, str] = Field(default_factory=dict)
    advice: str | None = None
    warning: str | None = None


@lru_cache(maxsize=1)
def load_docs() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"parameters": {}, "enums": {}, "sections": []}
    return json.loads(DATA_FILE.read_text())


def describe_parameter(name: str, value: Any) -> ParameterInfo:
    docs = load_docs()
    meta = docs["parameters"].get(name)
    info = ParameterInfo(name=name, value=value, known=meta is not None, advice=ADVICE.get(name))
    if meta is not None:
        info.type = meta["type"]
        info.default = meta["default"]
        info.section = meta["section"]
        info.doc = meta["doc"]
        if meta.get("enum"):
            info.enum_values = docs["enums"].get(meta["enum"], {})
    info.warning = _warning(name, value, info)
    return info


def _warning(name: str, value: Any, info: ParameterInfo) -> str | None:
    if not info.known:
        return "Unknown parameter for the OR-Tools version the docs were generated from."
    if name in SAFE:
        return None
    if name == "search_branching" and value == "FIXED_SEARCH":
        return (
            "FIXED_SEARCH disables the learned heuristics on all workers; expect slower solves "
            "unless your strategy is essential."
        )
    if name == "linearization_level":
        return (
            "Applied to all workers: the portfolio loses its LP diversity "
            "(no_lp/default_lp/max_lp all behave alike)."
        )
    if name == "cp_model_presolve" and value is False:
        return "Presolve is disabled; this usually makes the search much harder."
    if name in {"subsolvers", "ignore_subsolvers"}:
        return (
            "The default portfolio was changed; check the Solutions and Objective bounds tables "
            "to verify it helps."
        )
    if name == "use_lns_only":
        return "No exact worker runs: the solver cannot prove optimality or infeasibility."
    if any(fnmatch.fnmatch(name, pat) for pat in EXPENSIVE_PROPAGATION):
        return (
            "Expensive propagation set at the top level applies to every worker including the LNS "
            "helpers; consider a dedicated subsolver via subsolver_params/extra_subsolvers."
        )
    if name.startswith(("use_", "presolve_", "share_", "cp_model_", "symmetry_", "max_", "min_")):
        return (
            "Advanced parameter; changing it at the top level affects all workers of the portfolio."
        )
    return None


def describe_all(parameters: dict[str, Any]) -> list[ParameterInfo]:
    return [describe_parameter(name, value) for name, value in parameters.items()]

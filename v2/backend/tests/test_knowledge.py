"""The knowledge base (v2/knowledge/*.toml) must load and drive the API texts.

These tests are the safety net for CP-SAT experts editing the TOML files: a typo
that breaks a file, a missing section or an insight text whose placeholders do
not match the rule's fields fails here (and in ``python -m app.knowledge``).
"""

from __future__ import annotations

import string

from app import knowledge
from app.explanations import all_explanations, describe_subsolver
from app.parameters import describe_parameter

# Fields each insight rule passes to str.format (mirrors insights.py).
INSIGHT_FIELDS: dict[str, set[str]] = {
    "solved_by_presolve": set(),
    "not_proven_optimal": {"gap"},
    "no_solution": set(),
    "infeasible": set(),
    "solutions_stalled": {"last_time", "wall"},
    "bound_stalled": {"last_time", "wall"},
    "conflict_heavy": {"worker", "conflicts", "branches"},
    "feasible_descent": {"worker", "conflicts", "branches"},
    "per_worker_counters": {"response_conflicts", "max_conflicts"},
    "lns_closed_quickly": {"count", "total"},
    "presolve_expanded": {"initial", "presolved"},
    "presolve_shrank": {"initial", "presolved"},
}


def test_all_files_validate() -> None:
    """Every TOML file parses and has its required sections (what the CLI check does)."""
    assert knowledge.validate() == []


def test_insight_texts_use_known_fields() -> None:
    """A placeholder in insights.toml that the rule does not provide would crash at runtime."""
    rules = knowledge.load("insights")
    assert set(rules) == set(INSIGHT_FIELDS), "insights.py and insights.toml disagree on rules"
    for key, rule in rules.items():
        used = {f for _, f, _, _ in string.Formatter().parse(rule["text"]) if f}
        assert used <= INSIGHT_FIELDS[key], f"{key}: unknown placeholders {used}"


def test_subsolver_lookup_exact_prefix_pattern() -> None:
    """Names from real logs resolve: exact, versioned suffix (prefix rule) and glob fallback."""

    def doc(name: str):  # noqa: ANN202
        d = describe_subsolver(name)
        assert d is not None, name
        return d

    assert doc("rins_lns_default").summary == doc("rins").summary
    assert doc("objective_shaving_search_no_lp").role == "bound"
    assert doc("fj_short_default").role == "first_solution"
    assert doc("jump_decay_no_rst").role == "first_solution"
    assert describe_subsolver("weird_unknown_thing") is None


def test_explanations_endpoint_shape() -> None:
    """The frontend relies on these sections (see frontend/src/types.ts)."""
    ex = all_explanations()
    assert "search" in ex.blocks and "progress" in ex.cards
    assert "search_stats" in ex.tables and "Conflicts" in ex.tables["search_stats"].columns
    assert ex.constraints["kNoOverlap2D"].complexity in ex.constraint_complexity
    assert ex.domains.levels[-1].max_size is None and ex.domains.levels[0].max_size == 2
    assert ex.messages["closed_by_presolve"]
    assert set(ex.subsolver_roles) >= {d.role for d in ex.subsolvers.values()}


def test_parameter_warning_rules() -> None:
    """Rules from parameters.toml: safe -> none, value-specific, prefix fallback, unknown."""
    assert describe_parameter("max_time_in_seconds", 60).warning is None
    assert "FIXED_SEARCH" in (describe_parameter("search_branching", "FIXED_SEARCH").warning or "")
    assert describe_parameter("search_branching", "PORTFOLIO_SEARCH").warning is None
    assert "disabled" in (describe_parameter("cp_model_presolve", False).warning or "")
    assert "all workers" in (describe_parameter("use_probing_search", True).warning or "")
    assert "Not a parameter" in (describe_parameter("no_such_param", 1).warning or "")
    assert describe_parameter("num_workers", 8).advice


def test_labels_from_the_benchmark_corpus_are_documented() -> None:
    """Names harvested from the local benchmark corpus (``benchmarks/logs``) must resolve.

    Solving ~450 classic instances (QAP, set covering, RCPSP, ...) turned up event labels the
    example logs never showed: the bound labels of the core workers (``bool_<worker>``,
    ``am1_presolve``), the option-suffixed local-search copies and the RINS/RENS neighbourhood
    names. Each must reach a doc, otherwise the subsolver table shows a bare name.
    """
    for name in (
        "main",
        "bool_core",
        "bool_max_hs",
        "am1_presolve",
        "ls_restart",
        "ls_restart_decay_perturb",
        "fj_restart_compound_obj",
        "rins_lp_lns",
        "rens_pump_lns",
        "quick_restart_no_lp",
        "graph_dec_lns",
        "routing_full_path_lns",
    ):
        doc = describe_subsolver(name)
        assert doc is not None, name
        assert doc.summary


def test_empty_constraint_kind_is_documented() -> None:
    """``kEmpty`` (a proto with no constraint case set) occurs in real models, so explain it."""
    kinds = all_explanations().constraints
    assert "kEmpty" in kinds
    assert kinds["kEmpty"].complexity == "simple"


def test_worker_names_from_example_logs_are_documented() -> None:
    """Every worker name seen in the example logs' portfolio lines must resolve to a doc.

    Older OR-Tools versions use names such as ``random`` or ``rins/rens``; a missing doc
    would leave the UI without an explanation for that worker.
    """
    for name in ("random", "random_quick_restart", "rins/rens", "objective_shaving_search", "jump"):
        d = describe_subsolver(name)
        assert d is not None, name
        assert d.summary


def test_response_counters_are_not_attributed_to_the_first_full_worker() -> None:
    """The summary counters belong to the worker that finished first, not to `default_lp`.

    Verified on the benchmark corpus: in the 85 logs where the summary's `conflicts` matches
    exactly one Search stats row, that row is the first full worker in only 39 cases and a
    first-solution worker (`fs_random_no_lp`) in 29. The mechanism is
    `SharedResponseManager::AppendResponseToBeMerged` (stats are handed over when a worker is
    freed) plus `subsolver_responses_.front()` in the final merge. The old wording claimed the
    first full worker, so this guards against reintroducing it.
    """
    fields = knowledge.load("response_fields")["response_fields"]
    texts = [fields[f] for f in ("conflicts", "branches")]
    texts.append(knowledge.load("blocks")["blocks"]["response"])
    texts.append(knowledge.load("insights")["per_worker_counters"]["text"])
    for text in texts:
        assert "first full worker" not in text, text
    assert "finished first" in texts[0] or "finished first" in texts[-1]

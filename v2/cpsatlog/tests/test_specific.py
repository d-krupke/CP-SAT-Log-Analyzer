"""Exact values for selected example logs, one per major format variant."""

from __future__ import annotations

from cpsatlog import parse_log
from cpsatlog.schema import LineSpan, Table

from .conftest import read_example


def test_98_07_knapsack_tables_and_response() -> None:
    """9.8 log: standard tables, 13 solutions, OPTIMAL."""
    log = parse_log(read_example("98_07.txt"))
    assert log.solver is not None and log.solver.version is not None
    assert log.solver.version.value.startswith("9.8")
    assert log.response is not None
    assert log.response.status is not None and log.response.status.value == "OPTIMAL"

    solutions = log.stats.solutions
    assert isinstance(solutions, Table)
    assert solutions.count == 13
    core = solutions.row("core")
    assert core is not None and core.values == {"Num": 5, "Rank": "[4,8]"}
    assert core.line == 232

    search = log.stats.search_stats
    assert search is not None
    assert search.column("Conflicts")["core"] == 4759
    default_lp = search.row("default_lp")
    assert default_lp is not None and default_lp.line == 177

    timing = log.stats.task_timing
    assert timing is not None
    core_timing = timing.row("core")
    assert core_timing is not None
    assert core_timing.wall.n == 1
    assert abs(core_timing.wall.total - 0.5245) < 1e-9
    assert (
        core_timing.deterministic is not None
        and abs(core_timing.deterministic.total - 0.31117) < 1e-9
    )

    repos = log.stats.solution_repositories
    assert repos is not None
    pump = repos.row("pump")
    assert pump is not None and pump.values == {"Added": 0, "Queried": 0}


def test_93_legacy_format() -> None:
    """9.3 log: no fingerprint, key/value lists instead of tables, legacy stats dump."""
    log = parse_log(read_example("93_01.txt"))
    assert log.version == (9, 3, 10497)
    assert log.initial_model is not None and log.initial_model.fingerprint is None
    assert (
        log.initial_model.num_variables is not None and log.initial_model.num_variables.value == 290
    )
    assert log.initial_model.num_ints_in_objective is not None
    assert log.initial_model.num_ints_in_objective.value == 1
    assert log.presolve is not None
    assert log.presolve.steps[0].name == "ExtractEncodingFromLinear"
    assert (
        log.presolve.steps[0].time_s is not None
        and abs(log.presolve.steps[0].time_s - 9.558e-06) < 1e-12
    )
    assert log.search is not None
    assert log.search.start is not None and log.search.start.num_workers == 16
    assert log.search.subsolver_names("full")[:2] == ["default_lp", "no_lp"]
    assert log.search.subsolver_names("interleaved")[0] == "feasibility_pump"
    solutions = log.stats.solutions
    assert solutions is not None and solutions.column("Num") == {
        "no_lp": 1,
        "quick_restart_no_lp": 2,
    }
    assert log.search.objective_sense == "minimize"
    kinds = [e.kind for e in log.search.events]
    assert kinds.count("solution") == 3 and kinds.count("done") == 2 and kinds.count("bound") == 2
    # The initial_domain bound sits inside the "Preloading model." chunk and is still collected.
    first_bound = log.search.events_of_kind("bound")[0]
    assert first_bound.subsolver == "initial_domain" and first_bound.objective is None
    legacy = [m for m in log.messages if m.message_kind == "legacy_subsolver_stats"]
    assert legacy and legacy[0].span == LineSpan(start=62, end=141)  # nested per-subsolver dump
    assert log.unparsed == []


def test_915_newest_format() -> None:
    """9.15 log: new tables, LRAT line, fj_restart with rank 0, parameters dict."""
    log = parse_log(read_example("915_01.txt"))
    assert log.version == (9, 15, 6755)
    assert log.solver is not None and log.solver.parameters is not None
    assert log.solver.parameters.value == {
        "max_time_in_seconds": 5,
        "log_search_progress": True,
        "log_to_stdout": False,
        "num_workers": 8,
    }
    assert log.initial_model is not None
    assert log.initial_model.num_primary_variables is not None
    assert log.initial_model.num_primary_variables.value == 3018
    assert log.initial_model.constraints[-1].details == {"terms": 3000}
    assert log.stats.sat_formula is not None and log.stats.vivification is not None
    assert log.stats.clause_deletion is not None
    assert (
        log.stats.search_stats is not None and "BacktrackToRoot" in log.stats.search_stats.columns
    )
    assert log.stats.solutions is not None
    fj = log.stats.solutions.row("fj_restart")
    assert fj is not None and fj.values["Rank"] == "[0,1]"
    assert log.stats.improving_bounds_shared is not None
    assert log.stats.improving_bounds_shared.columns == ["Num", "Sym"]
    assert log.stats.clauses_shared is not None
    assert log.stats.clauses_shared.columns == [
        "#Exported",
        "#Imported",
        "#BinaryRead",
        "#BinaryTotal",
    ]
    assert log.response is not None
    assert log.response.lrat_status is not None and log.response.lrat_status.value == "NA"
    assert log.response.solution_fingerprint is not None
    assert log.response.objective is not None and log.response.objective.value == 34017
    assert log.search is not None and log.search.objective_sense == "maximize"
    assert log.search.events[0].subsolver == "initial_domain"  # printed inside the presolve block
    first = log.search.events_of_kind("solution")[0]
    assert first.subsolver == "fj_restart" and first.objective == 18963 and first.next_ub == 71066
    assert log.presolve is not None
    probe = next(s for s in log.presolve.steps if s.name == "Probe")
    assert probe.stats["probed"] == 3740 and probe.dtime_s is not None
    assert log.presolve_summary is not None and log.presolve_summary.affine_relations is not None
    assert log.presolve_summary.affine_relations.value == 4


def test_98_01_bound_inside_presolve_and_skipped_logs() -> None:
    log = parse_log(read_example("98_01.txt"))
    assert log.search is not None
    bound = log.search.events_of_kind("bound")[0]
    assert bound.line == 104 and bound.subsolver == "initial_domain"
    skipped = [e for e in log.search.events if e.skipped_logs is not None]
    assert skipped and skipped[0].skipped_logs == 3 and skipped[0].subsolver == "reduced_costs"
    assert log.presolve is not None and any(
        m.value == "Preloading model." for m in log.presolve.messages
    )


def test_presolve_closes_problem() -> None:
    """Some logs end right after presolve; the summary then knows it closed the problem."""
    for name in ("98_07.txt", "99_01.txt", "99_02.txt"):
        log = parse_log(read_example(name))
        if log.presolve_summary and log.presolve_summary.closed_by_presolve:
            assert log.search is None or not log.search.events_of_kind("solution")
            return
    raise AssertionError("expected one example that is closed by presolve")

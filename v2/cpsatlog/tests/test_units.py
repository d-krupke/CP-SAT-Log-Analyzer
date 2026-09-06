"""Unit tests for the small pure helpers: text parsing, parameters, events, splitter."""

from __future__ import annotations

from cpsatlog import parse_log
from cpsatlog.parsers.events import parse_event
from cpsatlog.parsers.parameters import parse_parameters
from cpsatlog.splitter import split_into_chunks, split_lines
from cpsatlog.text import parse_duration, parse_int, parse_number, split_columns, strip_row_name


def test_number_helpers() -> None:
    assert parse_int("3'020") == 3020
    assert parse_int("1.5") is None
    assert parse_number("1'392") == 1392
    assert parse_number("3.15e+11") == 3.15e11
    assert parse_number("[4,8]") is None
    assert parse_duration("524.50ms") == 0.5245
    assert parse_duration("0.00ns") == 0.0
    assert parse_duration("3.09s") == 3.09
    assert strip_row_name("'core':") == "core"
    assert strip_row_name("MIR_1:") == "MIR_1"
    assert split_columns("  3'153      4'759   [1,7]") == ["3'153", "4'759", "[1,7]"]


def test_parameters_nested_and_repeated() -> None:
    text = (
        'max_time_in_seconds: 30 log_search_progress: true name: "x y" '
        'subsolver_params { name: "a" linearization_level: 2 } '
        'subsolver_params { name: "b" } extra_subsolvers: "a" extra_subsolvers: "b" '
        "search_branching: FIXED_SEARCH relative_gap_limit: 0.01"
    )
    params = parse_parameters(text)
    assert params["max_time_in_seconds"] == 30
    assert params["log_search_progress"] is True
    assert params["name"] == "x y"
    assert params["subsolver_params"] == [{"name": "a", "linearization_level": 2}, {"name": "b"}]
    assert params["extra_subsolvers"] == ["a", "b"]
    assert params["search_branching"] == "FIXED_SEARCH"
    assert params["relative_gap_limit"] == 0.01


def test_event_variants() -> None:
    e = parse_event(
        "#12      0.71s best:17    next:[1,16]     quick_restart_no_lp fixed_bools:0/11849", 5
    )
    assert e is not None and e.kind == "solution" and e.solution_index == 12
    assert (e.objective, e.next_lb, e.next_ub, e.subsolver) == (17, 1, 16, "quick_restart_no_lp")

    e = parse_event("#Bound   0.66s best:inf   next:[]         objective_lb_search", 6)
    assert e is not None and e.kind == "bound" and e.objective is None and e.next_lb is None

    e = parse_event("#Model  10.01s var:7631/9999 constraints:14973/19703 [skipped_logs=5]", 7)
    assert e is not None and e.kind == "model" and e.model_vars == 7631 and e.skipped_logs == 5

    e = parse_event("#1       0.05s no_lp [hint]", 8)
    assert e is not None and e.kind == "solution" and e.subsolver == "no_lp" and e.tags == ["hint"]

    e = parse_event("#Done    2.98s objective_lb_search_no_lp", 9)
    assert e is not None and e.kind == "done" and e.subsolver == "objective_lb_search_no_lp"

    assert parse_event("Starting search at 0.1s with 8 workers.", 1) is None


def test_splitter_forced_cuts() -> None:
    text = (
        "Presolve summary:\n  - rule 'x' was applied 1 time.\nProblem closed by presolve.\n"
        "CpSolverResponse summary:\nstatus: OPTIMAL\n\n// comment\nSearch\n"
    )
    chunks = split_into_chunks(split_lines(text))
    assert [c.first for c in chunks] == [
        "Presolve summary:",
        "CpSolverResponse summary:",
        "// comment",
        "Search",
    ]
    assert (chunks[0].start, chunks[0].end) == (1, 3)
    assert (chunks[1].start, chunks[1].end) == (4, 5)


def test_task_timing_glued_to_the_search_block_is_cut_off() -> None:
    """CP-SAT prints the Task timing table without a blank line before it in some runs.

    Without the forced cut the whole table ends up inside the search block as unstructured
    lines: 62 of the 295 benchmark logs lost their Task timing table that way.
    """
    text = (
        "#1       0.01s best:12   next:[8,11]  default_lp\n"
        "Task timing                    n [     min,      max]      avg\n"
        "          'core':              1 [  4.90ms,   4.90ms]   4.90ms\n"
    )
    chunks = split_into_chunks(split_lines(text))
    assert [c.first.split()[0] for c in chunks] == ["#1", "Task"]

    log = parse_log(text)
    assert log.stats.task_timing is not None
    assert log.search is not None
    assert [e.kind for e in log.search.events] == ["solution"]


def test_parse_domain_shapes() -> None:
    """Domain lines become structured size/holes info; truncated lines keep only the bounds."""
    from cpsatlog.parsers.domain import parse_domain

    d = parse_domain("Booleans in [0,1]")
    assert d["kind"] == "bool" and d["size"] == 2 and d["intervals"] == 1
    d = parse_domain("in [0,12'864]")
    assert d["kind"] == "int" and (d["lo"], d["hi"], d["size"]) == (0, 12864, 12865)
    d = parse_domain("in [0][10][20,22]")
    assert d["size"] == 5 and d["intervals"] == 3 and d["hi"] == 22
    d = parse_domain("in [-5,-1][3]")
    assert (d["lo"], d["hi"], d["size"]) == (-5, 3, 6)
    d = parse_domain("constants in {2,3,4,5}")
    assert d["kind"] == "constant" and d["size"] == 4 and d["hi"] == 5
    d = parse_domain("in [0][910][1070][1 ... ][2245][2270][2500]")
    assert d["truncated"] and d["size"] is None and (d["lo"], d["hi"]) == (0, 2500)
    d = parse_domain("different domains in [0,12864] with a largest complexity of 3.")
    assert d["kind"] == "summary" and d["intervals"] == 3 and d["hi"] == 12864
    d = parse_domain("affine relations were detected.")
    assert d["kind"] == "other" and d["size"] is None


def test_model_line_component_sizes() -> None:
    """`compo:` on a #Model line lists connected-component sizes, not a worker name.

    Found in the benchmark corpus: the sizes were read as a subsolver called `compo`, which
    then showed up as an undocumented worker in the analysis.
    """
    ev = parse_event("#Model   0.01s var:485/485 constraints:263/263 compo:375,35,33,22,20", 7)
    assert ev is not None
    assert ev.kind == "model"
    assert ev.model_components == [375, 35, 33, 22, 20]
    assert not ev.model_components_truncated
    assert ev.subsolver is None


def test_model_line_truncated_component_sizes() -> None:
    """With more than ten components CP-SAT appends `,...`; the flag records that."""
    ev = parse_event(
        "#Model   0.2s var:9/9 constraints:4/4 compo:9,8,7,6,5,4,3,2,1,1,...", 8
    )
    assert ev is not None
    assert len(ev.model_components) == 10
    assert ev.model_components_truncated

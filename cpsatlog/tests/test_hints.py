"""Hint lines: every wording CP-SAT can print must be classified and located.

The solution hint is the caller's own input, so "was it accepted?" must be
answerable from the log. The wordings below are taken verbatim from
``SolutionHintIsCompleteAndFeasible`` and ``FixVariablesToHintValue`` in
``ortools/sat/cp_model_solver.cc``; the tricky part is that such a line is not a
block of its own (it appears inside the presolve block when presolve closes the
model), which is why the parser scans every line for it.
"""

from __future__ import annotations

from cpsatlog import parse_log
from cpsatlog.parsers.hints import parse_hint_note


def test_every_wording_is_classified() -> None:
    """Each hint line CP-SAT can print maps to its own kind, with its numbers."""
    cases = {
        "The solution hint is complete and is feasible.": ("hint_complete_feasible", {}),
        "The solution hint is complete and is feasible. Its objective value is 13.": (
            "hint_complete_feasible",
            {"objective": 13.0},
        ),
        "The solution hint is complete, but it is infeasible! we will try to repair it.": (
            "hint_complete_infeasible",
            {},
        ),
        "The solution hint is incomplete: 7 out of 42 non fixed variables hinted.": (
            "hint_incomplete",
            {"hinted": 7.0, "active": 42.0},
        ),
        # 9.8 and older left out "non fixed" (example_logs/archive).
        "The solution hint is incomplete: 2061 out of 80125 variables hinted.": (
            "hint_incomplete",
            {"hinted": 2061.0, "active": 80125.0},
        ),
        "The solution hint is complete but it contains values outside of the domain of the"
        " variables.": ("hint_outside_domain", {}),
        "The solution hint is complete and feasible, but it breaks the assumptions of the model.": (
            "hint_breaks_assumptions",
            {},
        ),
        "Fixing 12 variables to their value in the solution hints.": (
            "hint_fixed_variables",
            {"variables": 12.0},
        ),
        "Ignoring solution hint": ("hint_ignored", {}),
        "Using solution hint only as debug solution": ("hint_debug_only", {}),
        # A future rewording must stay visible instead of being dropped silently.
        "The solution hint smells funny.": ("hint_other", {}),
    }
    for line, (kind, numbers) in cases.items():
        note = parse_hint_note(line, 7)
        assert note is not None, line
        assert (note.kind, note.numbers, note.line) == (kind, numbers, 7), line


def test_unrelated_lines_are_not_hints() -> None:
    """The `[hint]` tag of an LNS line and the `fj solution hints` pool are something else."""
    for line in (
        "#17     1.20s best:42    next:[13,41]    graph_var_lns (d=0.20 s=15 t=0.10 p=0.00 [hint])",
        "   'fj solution hints':      9        0        9",
        "Starting search at 0.02s with 8 workers.",
    ):
        assert parse_hint_note(line, 1) is None


def test_hint_line_inside_the_presolve_block_is_still_found() -> None:
    """A hint checked after presolve is printed between `Preloading model.` and `#Model`.

    That block belongs to the presolve section, so a chunk-based parser never sees the line.
    Taken from the benchmark corpus (`dominating_set/jean`, presolve closes the model).
    """
    log = parse_log(
        "Starting CP-SAT solver v9.15.0\n"
        "\n"
        "Preloading model.\n"
        "#Bound   0.00s best:inf   next:[13,13]    initial_domain\n"
        "The solution hint is complete and is feasible. Its objective value is 13.\n"
        "#Model   0.00s var:0/0 constraints:0/0\n"
    )
    assert [(n.line, n.kind, n.numbers) for n in log.hints] == [
        (5, "hint_complete_feasible", {"objective": 13.0})
    ]
    # The line stays part of the presolve block; the hint list is the extra index.
    block = log.block_at(5)
    assert block is not None and block.kind == "presolve"


def test_standalone_hint_line_becomes_a_message_of_the_same_kind() -> None:
    """When the hint line stands alone it is a message block, and both agree on the kind."""
    log = parse_log(
        "Starting CP-SAT solver v9.15.0\n"
        "\n"
        "The solution hint is incomplete: 7 out of 42 non fixed variables hinted.\n"
    )
    assert [m.message_kind for m in log.messages] == ["hint_incomplete"]
    assert [n.kind for n in log.hints] == ["hint_incomplete"]
    assert not log.unparsed

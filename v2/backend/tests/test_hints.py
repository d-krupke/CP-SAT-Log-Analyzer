"""The solution-hint report (``app.hints``): the questions a user actually asks.

Created 2026-09 when hints got their own card: "did my hint arrive?", "did CP-SAT
use it?", "why does the log talk about a hint I never gave?". Each test builds the
smallest log that produces the signal, so the wording of one line can be checked
without a full example log. The corpus test guards the vacuous case, which is the
only hint wording the 295 benchmark logs contain.
"""

from __future__ import annotations

from cpsatlog import parse_log

from app.analysis import analyze
from app.hints import build_hint_report
from app.insights.triggers.hint import HintUsedAsFirstSolution, VacuousHintLine
from app.knowledge import load

HEADER = "Starting CP-SAT solver v9.15.0\n\n"


def _report(body: str):  # noqa: ANN202 - HintReport, kept short for readability
    return build_hint_report(parse_log(HEADER + body))


def test_no_hint_no_report() -> None:
    """A log without any hint line must not claim anything about hints."""
    report = _report("Starting search at 0.02s with 8 workers.\n")
    assert report.status == "none"
    assert not report.provided and not report.has_evidence


def test_complete_hint_solution_proves_the_hint_was_used() -> None:
    """After presolve CP-SAT logs nothing and pushes the hint into the pool as `complete_hint`.

    That solution event is the only evidence that the hint really became the incumbent, so it
    alone must be enough to report an accepted, used hint.
    """
    report = _report(
        "#1       0.03s best:42    next:[13,41]    complete_hint\n"
        "#2       0.31s best:38    next:[13,37]    default_lp\n"
    )
    assert report.status == "accepted"
    assert report.provided and report.used_as_first_solution
    assert report.first_solution_line == 3


def test_incomplete_hint_keeps_its_numbers() -> None:
    """`7 out of 42` is what the user needs to see: the hint was a preference, not a solution."""
    report = _report("The solution hint is incomplete: 7 out of 42 non fixed variables hinted.\n")
    assert (report.status, report.hinted, report.active) == ("incomplete", 7, 42)
    assert report.provided and not report.used_as_first_solution


def test_infeasible_hint_is_reported_as_such() -> None:
    report = _report(
        "The solution hint is complete, but it is infeasible! we will try to repair it.\n"
    )
    assert report.status == "infeasible" and report.provided


def test_the_later_check_decides() -> None:
    """CP-SAT checks the hint before and after presolve; the second verdict is the one that counts.

    Here presolve fixed variables until the hint covered them all, so the run went from an
    incomplete hint to a complete and feasible one.
    """
    report = _report(
        "The solution hint is incomplete: 7 out of 42 non fixed variables hinted.\n"
        "\n"
        "Presolved satisfaction model '': (model_fingerprint: 0x1)\n"
        "#Variables: 7 (7 primary variables)\n"
        "  - 7 Booleans in [0,1]\n"
        "\n"
        "The solution hint is complete and is feasible.\n"
    )
    assert report.status == "accepted"
    assert report.hinted == 7 and report.active == 42  # the earlier check is kept as detail
    assert len(report.notes) == 2


def test_ignored_hint_wins_over_a_verdict() -> None:
    """`cp_model_ignore_hints` drops the hint, so no verdict may be presented as its fate."""
    report = _report(
        "Ignoring solution hint\n\nThe solution hint is complete and is feasible.\n",
    )
    assert report.status == "ignored"


def test_fixed_variables_are_reported() -> None:
    """`fix_variables_to_their_hinted_value` turns the hint into hard constraints."""
    report = _report("Fixing 12 variables to their value in the solution hints.\n")
    assert report.fixed_variables == 12
    assert report.provided and report.status == "accepted"


def test_hint_line_without_a_hint_is_not_counted_as_a_hint() -> None:
    """With `#Variables: 0` the check trivially succeeds - the line says nothing about a hint.

    This is the only hint wording in the benchmark corpus (11 logs, e.g. every sudoku where
    presolve solves the puzzle). Reporting it as an accepted hint would be plainly wrong.
    """
    report = _report(
        "Presolved satisfaction model '': (model_fingerprint: 0xa5b85c5e198ed849)\n"
        "#Variables: 0 (0 primary variables)\n"
        "\n"
        "Preloading model.\n"
        "The solution hint is complete and is feasible.\n"
        "#Model   0.00s var:0/0 constraints:0/0\n"
    )
    assert report.status == "vacuous"
    assert not report.provided
    assert report.has_evidence  # the card still explains the line
    titles = [i.title for i in analyze(parse_log(HEADER + _VACUOUS)).insights]
    assert VacuousHintLine.title in titles


_VACUOUS = (
    "Presolved satisfaction model '': (model_fingerprint: 0xa5b85c5e198ed849)\n"
    "#Variables: 0 (0 primary variables)\n"
    "\n"
    "Preloading model.\n"
    "The solution hint is complete and is feasible.\n"
)


def test_used_hint_fires_the_good_insight() -> None:
    """The Overview must say it in words, not only in the hint card."""
    log = parse_log(HEADER + "#1       0.03s best:42    next:[13,41]    complete_hint\n")
    titles = [i.title for i in analyze(log).insights]
    assert HintUsedAsFirstSolution.title in titles


def _tile(body: str):  # noqa: ANN202 - Metric, kept short for readability
    metrics = analyze(parse_log(HEADER + body)).metrics
    return next(m for m in metrics if m.key == "hint")


def test_overview_states_that_there_was_no_hint() -> None:
    """ "Was a hint given?" must be answerable from the Overview, so the tile is always there.

    A missing hint is a finding, not an absence: it is the cheapest thing to try when the first
    solution comes late. Silence would leave the user unable to tell "no hint" from "the
    analyzer did not look".
    """
    tile = _tile("Starting search at 0.02s with 8 workers.\n")
    assert (tile.label, tile.value, tile.level) == ("Hint", "none", "info")
    assert tile.hint  # the tooltip explains what a hint is and when to try one


def test_overview_tile_reports_a_used_hint_as_good() -> None:
    tile = _tile("#1       0.03s best:42    next:[13,41]    complete_hint\n")
    assert (tile.value, tile.level) == ("used\nobjective 42", "good")
    assert tile.line == 3


def test_overview_tile_carries_the_numbers_of_an_incomplete_hint() -> None:
    """`7 of 42 vars` on the tile itself: the number is the point of that verdict."""
    tile = _tile("The solution hint is incomplete: 7 out of 42 non fixed variables hinted.\n")
    assert tile.value == "incomplete\n7 of 42 vars"


def test_the_vacuous_line_does_not_claim_a_hint_on_the_tile() -> None:
    tile = _tile(_VACUOUS)
    assert tile.value == "none"
    assert "presolve had already fixed every variable" in (tile.hint or "")


def test_every_hint_outcome_has_a_tile_text() -> None:
    """A status without a text in metrics.toml would raise KeyError while rendering."""
    from app.metrics import _HINT_TILE

    texts = load("metrics")["hint"]
    assert set(_HINT_TILE) <= set(texts), set(_HINT_TILE) - set(texts)


def test_the_objective_of_a_used_hint_comes_from_its_solution() -> None:
    """No line states the objective after presolve, but the `complete_hint` event does.

    The number is what makes the tile useful: it is the value to compare with the final
    objective, i.e. how much of the result the hint already brought along.
    """
    report = _report("#1       0.03s best:42    next:[13,41]    complete_hint\n")
    assert report.objective == 42
    assert _tile("#1       0.03s best:42    next:[13,41]    complete_hint\n").value == (
        "used\nobjective 42"
    )


def test_a_stated_hint_objective_wins_over_the_solution_event() -> None:
    """Both sources agree in practice; the line is the one CP-SAT computed for the hint."""
    report = _report(
        "The solution hint is complete and is feasible. Its objective value is 1146.\n"
        "#1       0.01s best:1146  next:[906,1145]  complete_hint\n"
    )
    assert report.objective == 1146

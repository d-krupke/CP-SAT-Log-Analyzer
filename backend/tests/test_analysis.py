"""Tests for the derived analysis (``app.analysis``) that need a hand-written log.

Created 2026-09-06 while mining the local benchmark corpus (``benchmarks/logs``): running the
analysis over 295 real logs showed that one insight trigger could never fire, because it
expected a number where CP-SAT prints a percentage. Tests here build the smallest log that
fires a trigger, so a threshold or a cell format can be checked without a full example log.
"""

from __future__ import annotations

from cpsatlog import parse_log

from app.analysis import analyze
from app.insights.triggers.lns import LnsClosedQuickly
from app.insights.triggers.presolve import ObjectiveRemovedByPresolve

LNS_TITLE = LnsClosedQuickly.title
OBJECTIVE_TITLE = ObjectiveRemovedByPresolve.title


def test_lns_closed_percentages_fire_the_insight() -> None:
    """The `Closed` column is printed as `90%`, so the rule must read percent cells.

    Regression: with numeric-only parsing the insight never fired on any real log (checked
    against 295 benchmark logs), because CP-SAT always prints this column with a percent sign.
    """
    log = parse_log(
        "Starting CP-SAT solver v9.15.0\n"
        "\n"
        "LNS stats                   Improv/Calls  Closed  Difficulty  TimeLimit\n"
        "          'graph_arc_lns':        12/131     90%    2.86e-01       0.10\n"
        "          'graph_cst_lns':        10/131     95%    3.35e-01       0.10\n"
        "          'graph_dec_lns':         9/130    100%    4.90e-01       0.10\n"
        "            'rnd_var_lns':         1/131      5%    3.29e-01       0.10\n"
    )
    titles = [i.title for i in analyze(log).insights]
    assert LNS_TITLE in titles


def test_low_closed_percentages_do_not_fire_the_insight() -> None:
    """Around 50% closed is the normal picture in the corpus and must stay quiet."""
    log = parse_log(
        "Starting CP-SAT solver v9.15.0\n"
        "\n"
        "LNS stats                   Improv/Calls  Closed  Difficulty  TimeLimit\n"
        "          'graph_arc_lns':        12/131     50%    2.86e-01       0.10\n"
        "          'graph_cst_lns':        10/131     48%    3.35e-01       0.10\n"
        "          'graph_dec_lns':         9/130     55%    4.90e-01       0.10\n"
    )
    titles = [i.title for i in analyze(log).insights]
    assert LNS_TITLE not in titles


def test_objective_removed_by_presolve_fires() -> None:
    """A presolved model line without objective terms means presolve fixed the objective.

    From the benchmark corpus (e.g. `binpacking/N1C1W1_A`): the initial line reports
    `(#ints: 1 in objective)` and the presolved one prints the empty form `( in objective)`.
    CP-SAT then drops every objective-based worker and all LNS neighborhoods, which is
    invisible in the log unless the portfolio is compared against a normal run.
    """
    log = parse_log(
        "Starting CP-SAT solver v9.15.6755\n"
        "\n"
        "Initial optimization model '': (model_fingerprint: 0x1)\n"
        "#Variables: 976 (#ints: 1 in objective) (925 primary variables)\n"
        "\n"
        "Presolved optimization model '': (model_fingerprint: 0x2)\n"
        "#Variables: 278 ( in objective) (254 primary variables)\n"
    )
    titles = [i.title for i in analyze(log).insights]
    assert OBJECTIVE_TITLE in titles


def test_objective_kept_by_presolve_stays_quiet() -> None:
    """The normal case: the presolved model still optimizes, so the insight must not fire."""
    log = parse_log(
        "Starting CP-SAT solver v9.15.6755\n"
        "\n"
        "Initial optimization model '': (model_fingerprint: 0x1)\n"
        "#Variables: 976 (#ints: 1 in objective) (925 primary variables)\n"
        "\n"
        "Presolved optimization model '': (model_fingerprint: 0x2)\n"
        "#Variables: 278 (#ints: 1 in objective) (254 primary variables)\n"
    )
    titles = [i.title for i in analyze(log).insights]
    assert OBJECTIVE_TITLE not in titles


def test_satisfaction_model_does_not_trigger_the_objective_insight() -> None:
    """A model that never had an objective must not look like one presolve emptied."""
    log = parse_log(
        "Starting CP-SAT solver v9.15.6755\n"
        "\n"
        "Initial satisfaction model '': (model_fingerprint: 0x1)\n"
        "#Variables: 256 (256 primary variables)\n"
        "\n"
        "Presolved satisfaction model '': (model_fingerprint: 0x2)\n"
        "#Variables: 150 (150 primary variables)\n"
    )
    titles = [i.title for i in analyze(log).insights]
    assert OBJECTIVE_TITLE not in titles

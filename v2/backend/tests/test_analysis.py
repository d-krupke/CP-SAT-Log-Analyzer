"""Tests for the derived analysis (``app.analysis``) that need a hand-written log.

Created 2026-09-06 while mining the local benchmark corpus (``benchmarks/logs``): running the
analysis over 295 real logs showed that one insight rule could never fire, because it expected
a number where CP-SAT prints a percentage. Tests here build the smallest log that triggers a
rule, so a threshold or a cell format can be checked without a full example log.
"""

from __future__ import annotations

from cpsatlog import parse_log

from app.analysis import analyze
from app.knowledge import load

LNS_TITLE = load("insights")["lns_closed_quickly"]["title"]


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

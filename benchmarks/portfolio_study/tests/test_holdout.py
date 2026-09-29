"""Tests for the Phase H instance selection (study/holdout.py).

The screen must accept a log whose objective still improves late with three active full
subsolvers, and reject the same log cut before 3 s or with only two active subsolvers;
the candidates skip Phase A and the small half of each list; the selection caps each class.
    uv run pytest portfolio_study/tests -q
"""

from cpsat_logutils import parse_log

from portfolio_study.study.holdout import Screen, candidates, passes_screen, select
from portfolio_study.tests.test_signals_metrics import LOG

# LOG: no_lp and max_lp find solutions, max_lp also bounds; add a bound for default_lp.
THREE_ACTIVE = LOG.replace(
    "   'max_lp':    3\n", "   'max_lp':    3\n   'default_lp':    1\n", 1
)


def test_screen_accepts_late_improvement_with_three_active_full_subsolvers():
    assert passes_screen(parse_log(THREE_ACTIVE)).passed


def test_screen_rejects_two_active_or_no_late_improvement():
    two = passes_screen(parse_log(LOG))
    assert not two.passed and "2 active" in two.reason
    early = "\n".join(
        line for line in THREE_ACTIVE.splitlines() if not line.startswith(("#3", "#4"))
    )
    assert not passes_screen(parse_log(early)).passed


def test_candidates_take_the_larger_half_without_phase_a():
    listing = {
        "jobshop": ["ft06", "la01", "swv06", "ta61", "yn1", "ta21"],
        "sudoku": ["a", "b"],
    }
    assert candidates(listing) == [
        ("jobshop", "yn1"),
        ("jobshop", "ta21"),
    ]  # swv06/ta61: small half


def test_select_caps_per_class_in_order():
    ok, bad = Screen(True, ""), Screen(False, "")
    screened = [
        ("a", "1", ok),
        ("a", "2", bad),
        ("a", "3", ok),
        ("a", "4", ok),
        ("b", "1", ok),
    ]
    assert select(screened, per_class=2) == [("a", "1"), ("a", "3"), ("b", "1")]

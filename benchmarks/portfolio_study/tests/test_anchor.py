"""late_anchor pins default_lp to the top and otherwise keeps the `late` order.
Created 2026-09-27 with the anchored metric (Phase D of the portfolio study)."""

from cpsat_logutils import parse_log

from portfolio_study.study.metrics import late_anchor, late_share
from portfolio_study.study.signals import extract_signals
from portfolio_study.tests.test_signals_metrics import LOG


def test_default_lp_is_pinned_first_and_the_rest_keeps_the_late_order():
    """In the synthetic log default_lp improved nothing and `late` ranks it last; the
    anchored variant moves it to the front without reordering no_lp and max_lp."""
    sig = extract_signals(parse_log(LOG), time_limit=10.0)
    assert late_share(sig)[-1] == "default_lp"
    assert late_anchor(sig) == ["default_lp", *[n for n in late_share(sig) if n != "default_lp"]]

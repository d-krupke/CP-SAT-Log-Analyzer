"""Tests for the "Give LNS more threads" hint (``app.lns_hint``).

Created 2026-09-28 with the hint. The study behind it (portfolio_study, Phases G and H)
only supports it when the LNS pool delivered >= half of the time-weighted progress, at 8-12
workers, and when the user has not set the split already; each test pins one of these
conditions. Variants must count as their pool entry (`ls_*` as `ls`, `rins_lp_lns` as
`rins/rens`, `lb_relax_lns_bool` as `lb_relax_lns`; added 2026-09-29 after a review found the
last two uncounted), first-solution workers not.
"""

from __future__ import annotations

from cpsat_logutils import parse_log

from app.importance import build_ranking
from app.knowledge import load
from app.lns_hint import pool_member
from tests.test_importance import FULL6, HEADER, _log

# Weighted: no_lp 50*1 = 50; rnd_var_lns 100*4 = 400; ls variant 50*6 = 300 -> pool 700/750.
LNS_EVENTS = """#1       0.10s best:1000  next:[0,999] fj
#2       1.00s best:950   next:[0,949] no_lp
#3       4.00s best:850   next:[0,849] rnd_var_lns (d=5.00e-01 s=15 t=0.10 p=0.00 stall=0 h=base)
#4       6.00s best:800   next:[0,799] ls_restart_decay(batch:1)
#Done    9.00s no_lp
"""

# Weighted: no_lp 400*5 = 2000, rnd_var_lns 100*2 = 200 -> pool 200/2200 < 0.5.
FULL_EVENTS = """#1       0.10s best:1000  next:[0,999] fj
#2       2.00s best:900   next:[0,899] rnd_var_lns (d=5.00e-01 s=15 t=0.10 p=0.00 stall=0 h=base)
#3       5.00s best:500   next:[0,499] no_lp
#Done    9.00s no_lp
"""


def _hint(events: str, workers: int = 8, full_line: str | None = None):
    kwargs = {"full_line": full_line} if full_line else {}
    ranking = build_ranking(_log(events, workers=workers, **kwargs))
    assert ranking is not None
    return ranking.lns_hint


def test_hint_when_lns_carried_the_run():
    """Pool share 700/750; 8 workers with 6 full strategies -> suggest 4, with the numbers
    in the text and a copyable parameter line."""
    hint = _hint(LNS_EVENTS)
    assert hint is not None
    assert abs(hint.share - 700 / 750) < 1e-9
    assert (hint.workers, hint.full, hint.suggested_full) == (8, 6, 4)
    assert "93%" in hint.text and "num_full_subsolvers = 4" in hint.text
    assert hint.snippet == "solver.parameters.num_full_subsolvers = 4"


def test_no_hint_when_full_strategies_carried_the_run():
    assert _hint(FULL_EVENTS) is None


def test_no_hint_outside_the_tested_worker_range():
    """4 workers (3 full) was never tested: no hint, however high the LNS share."""
    full3 = "3 full problem subsolvers: [default_lp, fixed, no_lp]"
    assert _hint(LNS_EVENTS, workers=4, full_line=full3) is None
    cfg = load("importance")["lns"]
    assert cfg["min_workers"] <= 8 <= cfg["max_workers"]


def test_no_hint_when_the_split_was_set_by_the_user():
    """`num_full_subsolvers` in the parameters: the user already chose, say nothing."""
    text = HEADER.format(workers=8, full_line=FULL6) + LNS_EVENTS
    text = text.replace("num_workers: 8", "num_workers: 8 num_full_subsolvers: 6")
    ranking = build_ranking(parse_log(text))
    assert ranking is not None and ranking.lns_hint is None


def test_no_hint_when_the_run_was_solved():
    """The study only tested runs stopped by the time limit (status FEASIBLE)."""
    response = "\nCpSolverResponse summary:\nstatus: OPTIMAL\nobjective: 800\n"
    ranking = build_ranking(_log(LNS_EVENTS, tail=response))
    assert ranking is not None and ranking.lns_hint is None
    feasible = build_ranking(_log(LNS_EVENTS, tail=response.replace("OPTIMAL", "FEASIBLE")))
    assert feasible is not None and feasible.lns_hint is not None


def test_pool_member_maps_variants_to_their_pool_entry():
    """The solution lines name variants; the pool lists the switchable worker. The longest
    matching entry wins (`ls_lin_*` is `ls_lin`, not `ls`); first-solution names stay out."""
    pool = {"ls", "ls_lin", "rins/rens", "lb_relax_lns", "graph_arc_lns"}
    assert pool_member("graph_arc_lns", pool) == "graph_arc_lns"
    assert pool_member("ls_restart_decay", pool) == "ls"
    assert pool_member("ls_lin_restart", pool) == "ls_lin"
    assert pool_member("rins_lp_lns", pool) == "rins/rens"
    assert pool_member("rens_pump_lns", pool) == "rins/rens"
    assert pool_member("lb_relax_lns_bool_h", pool) == "lb_relax_lns"
    assert pool_member("fj_restart", pool) is None
    assert pool_member("rins_lp_lns", {"ls"}) is None


def test_rins_and_lb_relax_variants_count_toward_the_share():
    """Weighted: no_lp 50*1 = 50, rins_lp_lns 100*4 = 400, lb_relax_lns_bool 50*6 = 300 ->
    pool 700/750, the same run as LNS_EVENTS with other neighborhoods. Before the fix the
    share was 0 and no hint was shown."""
    events = LNS_EVENTS.replace("rnd_var_lns (d=5", "rins_lp_lns (d=5").replace(
        "ls_restart_decay(batch:1)", "lb_relax_lns_bool (d=5.00e-01 s=15 t=0.10)"
    )
    text = HEADER.format(workers=8, full_line=FULL6).replace(
        "3 interleaved subsolvers: [graph_arc_lns, ls, rnd_var_lns]",
        "3 interleaved subsolvers: [graph_arc_lns, lb_relax_lns, rins/rens]",
    )
    ranking = build_ranking(parse_log(text + events))
    assert ranking is not None and ranking.lns_hint is not None
    assert abs(ranking.lns_hint.share - 700 / 750) < 1e-9

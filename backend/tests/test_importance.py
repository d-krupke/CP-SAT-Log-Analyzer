"""Tests for the portfolio ranking (``app.importance``).

Created 2026-09-28 with the ranking. The logs are hand-written so each test states the
numbers it relies on: the ranking must follow the *size and time* of the improvements, not
their count (the lesson of the portfolio-importance study), and the texts must degrade
honestly when the log gives little to rank.
"""

from __future__ import annotations

from cpsat_logutils import parse_log

from app.analysis import analyze
from app.importance import build_ranking, full_subsolver_count, objective_shares
from app.knowledge import load

HEADER = """Starting CP-SAT solver v9.15.6755
Parameters: max_time_in_seconds: 10 num_workers: {workers}

Initial optimization model '': (model_fingerprint: 0x1)
#Variables: 10 (#ints: 10 in objective)
  - 10 in [0,100]
#kLinearN: 1

Starting search at 0.02s with {workers} workers.
{full_line}
2 first solution subsolvers: [fj, fs_random_no_lp]
3 interleaved subsolvers: [graph_arc_lns, ls, rnd_var_lns]

"""

FULL6 = (
    "6 full problem subsolvers: [default_lp, fixed, max_lp, no_lp, quick_restart, reduced_costs]"
)


def _log(events: str, workers: int = 8, full_line: str = FULL6, tail: str = ""):
    return parse_log(HEADER.format(workers=workers, full_line=full_line) + events + tail)


# no_lp makes one big improvement late; quick_restart makes many tiny ones; the LNS a middle one.
EVENTS = """#1       0.10s best:1000  next:[0,999] fj
#2       1.00s best:990   next:[0,989] quick_restart
#3       1.10s best:989   next:[0,988] quick_restart
#4       1.20s best:988   next:[0,987] quick_restart
#5       1.30s best:987   next:[0,986] quick_restart
#6       2.00s best:887   next:[0,886] rnd_var_lns (d=5.00e-01 s=15 t=0.10 p=0.00 stall=0 h=base)
#7       5.00s best:487   next:[0,486] no_lp
#Done    9.00s no_lp
"""

BOUNDS = """
Objective bounds     Num
  'reduced_costs':    7
"""


def test_worker_split_matches_cp_sat():
    """F(n) as observed in CP-SAT 9.15 runs: 3->2, 4->3, 6->4, 7->5, 8->6, 12->8."""
    assert [full_subsolver_count(n) for n in (1, 2, 3, 4, 6, 7, 8, 12)] == [1, 1, 2, 3, 4, 5, 6, 8]


def test_shares_follow_improvement_size_not_count():
    """Total improvement 513: no_lp 400, LNS 100, quick_restart 4 x 1-10. The plain shares sum
    to 1 over all finders; the first solution (fj) improves nothing and gets no share."""
    shares = objective_shares(_log(EVENTS))
    assert "fj" not in shares
    assert abs(sum(s.share for s in shares.values()) - 1) < 1e-9
    assert abs(shares["no_lp"].share - 400 / 513) < 1e-9
    assert shares["quick_restart"].improvements == 4
    assert shares["no_lp"].weighted > shares["no_lp"].share  # it came late


def test_ranking_verdicts_and_worker_choices():
    """no_lp carried; quick_restart contributed despite the most solutions; default_lp and
    fixed are backbone (never labelled useless); reduced_costs only improved bounds; max_lp is
    shadowed. At 4 workers (3 full) CP-SAT keeps default_lp, fixed, no_lp; the log suggests
    no_lp, quick_restart, then default_lp (ties keep CP-SAT's order)."""
    ranking = build_ranking(_log(EVENTS, tail=BOUNDS))
    assert ranking is not None
    verdicts = {r.name: r.verdict for r in ranking.ranked}
    assert [r.name for r in ranking.ranked][:3] == ["no_lp", "quick_restart", "default_lp"]
    assert verdicts == {
        "no_lp": "carried",
        "quick_restart": "contributed",
        "default_lp": "backbone",
        "fixed": "backbone",
        "max_lp": "shadowed",
        "reduced_costs": "bound",
    }
    at4 = next(c for c in ranking.choices if c.workers == 4)
    assert at4.full == 3
    assert at4.default == ["default_lp", "fixed", "no_lp"]
    assert at4.ranked == ["no_lp", "quick_restart", "default_lp"]
    assert [c.workers for c in ranking.choices] == [2, 3, 4, 5, 6, 7]
    assert ranking.caveats == []


def test_caveats_for_many_full_subsolvers_and_custom_portfolios():
    """Eight full subsolvers (12 workers) is the largest tested portfolio: no caveat. Eleven
    (16 workers) exceed it; a `subsolvers` override changes what 'default' means. Both are
    said, in the knowledge-base wording."""
    full8 = (
        "8 full problem subsolvers: [default_lp, fixed, max_lp, no_lp, pseudo_costs,"
        " quick_restart, quick_restart_no_lp, reduced_costs]"
    )
    caveats = load("importance")["caveats"]
    tested = build_ranking(parse_log(HEADER.format(workers=12, full_line=full8) + EVENTS))
    assert tested is not None and tested.caveats == []
    full11 = full8.replace("8 full", "11 full").replace(
        "reduced_costs]", "reduced_costs, core, probing, lb_tree_search]"
    )
    text = HEADER.format(workers=16, full_line=full11).replace(
        "num_workers: 16", 'num_workers: 16 subsolvers: "no_lp"'
    )
    ranking = build_ranking(parse_log(text + EVENTS))
    assert ranking is not None
    assert caveats["many_full"] in ranking.caveats
    assert caveats["custom_portfolio"] in ranking.caveats


def test_repeated_strategies_count_as_threads():
    """`default_lp(3)` and `shared_tree(6)` are 9 threads, not 2 names: 13 full threads exceed
    the tested 8 even though only 6 names are listed. `shared_tree` is ranked like any other
    worker but never offered for `subsolvers`, which cannot select it."""
    full = (
        "13 full problem subsolvers: [default_lp(3), max_lp, no_lp, quick_restart,"
        " quick_restart_no_lp, shared_tree(6)]"
    )
    events = EVENTS.replace("#5       1.30s best:987   next:[0,986] quick_restart",
                            "#5       1.30s best:987   next:[0,986] shared_tree")  # fmt: skip
    ranking = build_ranking(_log(events, workers=16, full_line=full))
    assert ranking is not None
    assert load("importance")["caveats"]["many_full"] in ranking.caveats
    assert "shared_tree" in [r.name for r in ranking.ranked]
    assert all("shared_tree" not in c.ranked + c.default for c in ranking.choices)


def test_num_full_subsolvers_counts_as_a_custom_portfolio():
    """Setting the thread split changes what CP-SAT keeps, so the comparison needs the caveat."""
    text = HEADER.format(workers=8, full_line=FULL6).replace(
        "num_workers: 8", "num_workers: 8 num_full_subsolvers: 6"
    )
    ranking = build_ranking(parse_log(text + EVENTS))
    assert ranking is not None
    assert load("importance")["caveats"]["custom_portfolio"] in ranking.caveats


def test_nothing_to_rank():
    """A single full subsolver or a run without improvements yields no card at all."""
    one = "1 full problem subsolvers: [default_lp]"
    assert build_ranking(_log(EVENTS, workers=2, full_line=one)) is None
    assert build_ranking(_log("#1       0.10s best:1000  next:[0,999] fj\n")) is None


def test_analysis_carries_ranking_and_shares():
    """The API model exposes the ranking and each worker's plain share (contributions card)."""
    analysis = analyze(_log(EVENTS))
    assert analysis.portfolio_ranking is not None
    by_name = {s.name: s for s in analysis.subsolvers}
    assert abs((by_name["rnd_var_lns"].objective_share or 0) - 100 / 513) < 1e-9

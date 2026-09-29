"""Tests for the pure parts of the portfolio study: signals, metrics, primal measures.

A small synthetic log (two full subsolvers, four improving solutions, the per-subsolver
tables) checks that improvement shares are attributed to the finder and sum to one, that
late improvements weigh more, that metrics fall back to the default order on ties, and
that the primal integral matches a hand computation.
    uv run pytest portfolio_study/tests -q
"""

from cpsat_logutils import parse_log

from portfolio_study.study.evaluate import primal
from portfolio_study.study.metrics import (
    METRICS,
    default_order,
    improvement_share,
    last_solution_rank,
    late_share,
)
from portfolio_study.study.signals import extract_signals

LOG = """Starting search at 0.00s with 4 workers.
3 full problem subsolvers: [default_lp, max_lp, no_lp]
13 interleaved subsolvers: [graph_arc_lns, rnd_var_lns]

#1       1.00s best:100   next:[0,99]    no_lp
#2       2.00s best:80    next:[0,79]    max_lp
#3       5.00s best:70    next:[0,69]    rnd_var_lns
#4       9.00s best:60    next:[0,59]    no_lp
#Done   10.00s max_lp

Solutions (4)    Num   Rank
  'max_lp':    1  [2,2]
   'no_lp':    2  [0,3]
  'rnd_var_lns':    1  [1,1]

Objective bounds     Num
   'max_lp':    3

Improving bounds shared    Num  Sym
            'default_lp':    8    0
                'max_lp':    2    0
"""


def test_signals_attribute_improvements_to_the_finder():
    sig = extract_signals(parse_log(LOG), time_limit=10.0)
    assert set(sig) == {"default_lp", "max_lp", "no_lp"}
    no_lp, max_lp, dlp = sig["no_lp"], sig["max_lp"], sig["default_lp"]
    # total improvement 100 -> 60 = 40: max_lp 20 (0.5), lns 10, no_lp 10 (0.25)
    assert abs(max_lp.improvement_share - 0.5) < 1e-9
    assert abs(no_lp.improvement_share - 0.25) < 1e-9
    assert dlp.improvement_share == 0.0
    # late share: max_lp's 0.5 at t=2 -> 0.1; no_lp's 0.25 at t=9 -> 0.225 (later counts more)
    assert abs(max_lp.late_share - 0.1) < 1e-9
    assert abs(no_lp.late_share - 0.225) < 1e-9
    assert no_lp.found_first and not max_lp.found_first
    assert no_lp.n_solutions == 2 and no_lp.first_rank == 0 and no_lp.last_rank == 3
    assert no_lp.last_rank_share == 1.0 and abs(max_lp.last_rank_share - 2 / 3) < 1e-9
    assert no_lp.found_best and not max_lp.found_best
    assert max_lp.n_bounds == 3 and max_lp.done
    assert dlp.shared_bounds == 8
    assert [dlp.default_rank, no_lp.default_rank, max_lp.default_rank] == sorted([dlp.default_rank, no_lp.default_rank, max_lp.default_rank])


def test_metrics_order_and_fall_back_to_default():
    sig = extract_signals(parse_log(LOG), time_limit=10.0)
    assert default_order(sig) == ["default_lp", "no_lp", "max_lp"]
    assert improvement_share(sig) == ["max_lp", "no_lp", "default_lp"]
    assert late_share(sig) == ["no_lp", "max_lp", "default_lp"]
    assert last_solution_rank(sig) == ["no_lp", "max_lp", "default_lp"]
    for name, metric in METRICS.items():
        order = metric(sig)
        assert sorted(order) == sorted(sig), name


def test_primal_integral_matches_hand_computation():
    p = primal(parse_log(LOG), best_known=60.0, time_limit=10.0)
    # gap: 1.0 for t<1, (100-60)/60 -> capped 0.667 on [1,2), 0.333 on [2,5), 0.167 on [5,9), 0 after
    expected = 1.0 * 1 + (40 / 60) * 1 + (20 / 60) * 3 + (10 / 60) * 4 + 0.0
    assert abs(p.integral - expected) < 1e-9
    assert p.final == 60.0 and p.final_gap == 0.0 and p.first_time == 1.0 and p.n_solutions == 4


def test_learned_and_v3_are_permutations_of_the_names():
    """Frozen-weight metrics must return every full subsolver exactly once, and the name prior
    must be able to lift a subsolver that the log alone ranks last (v3 with a prior of 0.74
    for default_lp still ranks max_lp first because the log-based rank dominates)."""
    from portfolio_study.study.metrics import learned, primal_v2, primal_v3

    sig = extract_signals(parse_log(LOG), time_limit=10.0)
    for metric in (learned, primal_v3):
        assert sorted(metric(sig)) == sorted(sig)
    assert primal_v3(sig)[0] == primal_v2(sig)[0]


def test_primal_v4_prefers_magnitude_over_count():
    """Only magnitude counts: the two workers that improved the objective (max_lp half of it
    early, no_lp a quarter but late) both rank ahead of default_lp, which found the first
    solution but improved nothing; no_lp edges out max_lp because its share of the *late*
    improvement is larger (0.69 vs 0.31) than its deficit in total share (0.33 vs 0.67)."""
    from portfolio_study.study.metrics import primal_v4

    sig = extract_signals(parse_log(LOG), time_limit=10.0)
    assert primal_v4(sig) == ["no_lp", "max_lp", "default_lp"]

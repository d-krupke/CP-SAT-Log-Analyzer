"""Tests for the LNS-pool signals and pruning rules of Phase G (study/lns.py).

A synthetic log with six pool names: two LNS neighborhoods and the `ls` worker report
improving solutions (the `ls_*` variant must be folded into `ls`), the LNS stats table
separates the idle neighborhoods by their local improvement rate. Checks: attribution,
ranking with the rate as tie-breaker, and that every pruning rule keeps KEEP_MIN names.
    uv run pytest portfolio_study/tests -q
"""

from cpsat_logutils import parse_log

from portfolio_study.study.lns import (
    KEEP_MIN,
    pool_signals,
    prune_idle,
    prune_random,
    prune_top,
    ranked,
)

LOG = """Starting search at 0.00s with 8 workers.
6 full problem subsolvers: [default_lp, fixed, max_lp, no_lp, quick_restart, reduced_costs]
6 interleaved subsolvers: [feasibility_pump, graph_arc_lns, graph_var_lns, ls, rins/rens, rnd_var_lns]

#1       1.00s best:100   next:[0,99]    no_lp
#2       2.00s best:90    next:[0,89]    graph_arc_lns (d=5.00e-01 s=15 t=0.10 p=0.00 stall=0 h=base)
#3       5.00s best:80    next:[0,79]    ls_restart_decay(batch:1 lin{mvs:0 evals:0} gen{mvs:1 evals:0} comp{mvs:0 btracks:0} #w_updates:0 #perturb:0)
#4       8.00s best:60    next:[0,59]    rnd_var_lns (d=5.00e-01 s=15 t=0.10 p=0.00 stall=0 h=base)
#Done   10.00s no_lp

LNS stats                Improv/Calls  Closed  Difficulty  TimeLimit
      'graph_arc_lns':           2/4     50%    5.00e-01       0.10
      'graph_var_lns':           3/4     50%    5.00e-01       0.10
          'rins/rens':           0/4     50%    5.00e-01       0.10
        'rnd_var_lns':           1/4     50%    5.00e-01       0.10
"""


def test_attribution_folds_ls_variants_and_weights_by_time():
    """Weighted deltas: arc 10*2=20, ls 10*5=50, rnd 20*8=160, no_lp is a full worker (not in
    the pool) and #1 improves nothing. Pool shares are relative to all improvements."""
    sig = pool_signals(parse_log(LOG), 10.0)
    assert set(sig) == {
        "feasibility_pump",
        "graph_arc_lns",
        "graph_var_lns",
        "ls",
        "rins/rens",
        "rnd_var_lns",
    }
    assert abs(sig["rnd_var_lns"].late_share - 160 / 230) < 1e-9
    assert abs(sig["ls"].late_share - 50 / 230) < 1e-9
    assert sig["graph_var_lns"].late_share == 0 and sig["graph_var_lns"].rate == 0.75


def test_ranking_uses_rate_as_tiebreak_and_pruning_keeps_the_minimum():
    """rnd_var, ls, arc have shares; graph_var (rate .75) beats rins/rens (0) and the
    pump (no calls; equal rates fall back to the name). prune_idle keeps max(KEEP_MIN, 3) = 4 and drops the last two."""
    sig = pool_signals(parse_log(LOG), 10.0)
    assert ranked(sig) == [
        "rnd_var_lns",
        "ls",
        "graph_arc_lns",
        "graph_var_lns",
        "feasibility_pump",
        "rins/rens",
    ]
    assert prune_idle(sig) == ["feasibility_pump", "rins/rens"]
    assert prune_top(sig, 5) == ["rnd_var_lns", "ls"]  # capped at len - KEEP_MIN
    rnd = prune_random(sig, 2, "x")
    assert len(rnd) == 2 and rnd == prune_random(
        sig, 2, "x"
    )  # deterministic in the key
    assert len(sig) - len(prune_random(sig, 9, "y")) == KEEP_MIN


def test_rins_and_lb_relax_variants_fold_into_their_pool_entry():
    """`rins_lp_lns` reports for `rins/rens`, `lb_relax_lns_bool` for `lb_relax_lns` (added
    2026-09-29: both were dropped before, which understated the pool share). The old
    attribution stays available for rebuilding the Phase G pruning arms."""
    log = parse_log(
        LOG.replace("graph_arc_lns (d=", "rins_lp_lns (d=")
        .replace("rnd_var_lns (d=", "lb_relax_lns_bool (d=")
        .replace("rnd_var_lns]", "lb_relax_lns]")
    )
    sig = pool_signals(log, 10.0)
    assert abs(sig["rins/rens"].late_share - 20 / 230) < 1e-9
    assert abs(sig["lb_relax_lns"].late_share - 160 / 230) < 1e-9
    old = pool_signals(log, 10.0, fold_variants=False)
    assert old["rins/rens"].late_share == 0 and old["lb_relax_lns"].late_share == 0
    assert abs(old["ls"].late_share - 50 / 230) < 1e-9

# Which CP-SAT portfolio strategies matter? A log-based importance metric and its verification

Written 2026-09-27 as the closing report of the portfolio-importance study in this directory
(`PLAN.md` holds the running log with all intermediate numbers; `study/` the code;
`experiments/` the runnable phases; `runs/` the 1305 cached solver runs, git-ignored).
Read this first when you want to (a) rank the full subsolvers of a CP-SAT log by how much
they contributed to the *primal* side, (b) understand why the obvious counting metrics are
wrong, or (c) re-run or extend the verification. CP-SAT 9.15, 10 s runs, 12 physical cores.

## 1. Question and protocol

Given one log with the portfolio (`default_lp`, `no_lp`, `max_lp`, `quick_restart`,
`reduced_costs`, `core`, `fixed`, ...), order the full subsolvers by importance such that,
with fewer workers, keeping the top-k of that order beats keeping CP-SAT's default first-k.

* CP-SAT runs F(n) full subsolvers at n workers: 1 for n=1, n-1 for n<=4, n-2 for n<=8,
  and the rest are first-solution and LNS/LS workers. The default at n is the first F(n)
  applicable names of its list (`default_lp, fixed, core, no_lp, max_lp, quick_restart,
  reduced_costs, ...`). The `subsolvers` whitelist replaces that list and keeps the thread
  split, so *default at n* vs *top-F(n) by metric at n* is a fair, paired comparison.
* Only the primal side is measured: final primal gap and primal integral over the 10 s
  (gap = 1 before the first solution), against the best objective known from all runs. Proof
  time is deliberately ignored: on most instances it dominates the log and would measure
  nothing about the objective search.
* 12 instances from 9 problem classes (job shop x2, flexible job shop, cvrp x2, multi
  knapsack x2, golomb ruler, set covering, strip packing, gap, qap), selected in a screening
  phase as portfolio-sensitive (different subsolvers find the improvements) and not solved
  to optimality in 10 s.
* Noise: two runs with different seeds differ by 0-3 % in objective, 13 % on cvrp/A-n80-k10.
  All comparisons are paired by seed and counted as wins/losses across seeds 0 and 1 and
  worker counts n in {2, 3, 4, 6, 7}. Pairs where the metric's top-F set equals the default
  set are excluded and used as a noise estimate.

## 2. Ground truth for the metric (Phase B)

Two ablations were run to have something to correlate an ordering against:

* **Leave-one-out at 7 workers** (drop one of six): within noise on 10 of 12 instances. The
  portfolio is redundant enough, and the LNS pool strong enough, that a single removal is
  invisible in 10 s. Consequence: "blacklist the least important one" cannot be verified at
  this budget, and no metric correlates with the LOO order (|rho| < 0.15).
* **Solo at 2 workers** (that subsolver plus one LNS thread), 3 seeds: strongly
  discriminative and instance-dependent. Best solo worker: `no_lp` on job shop, golomb,
  strip packing; `default_lp` on cvrp, set covering, flexible job shop; `reduced_costs` on
  both knapsack instances; `max_lp` on gap; `core` on qap. `reduced_costs` is the worst solo
  worker on 10 of 12 instances (a pure bound worker) but the best on knapsack.

Spearman correlation between metric orderings (from the 8-worker log) and the solo order,
mean over 12 instances: time-weighted magnitude share 0.69, ridge regression on ten
normalized features 0.67 out-of-sample (0.73 in-sample), improvement magnitude share 0.61,
solution count 0.63, CP-SAT's default order 0.27, conflicts 0.23. Twelve instances are too
few to learn weights that beat hand-made ones.

## 3. What the verification showed (Phase C)

Ranked top-F(n) vs default at n, seeds 0 and 1, ~83 informative pairs per metric.
Negative dPI = ranked portfolio better (primal integral, gap units x seconds).

| metric | what it scores | PI wins/losses | sign test p | mean dPI |
|---|---|---|---|---|
| **late** | share of the objective improvement, each improvement weighted by t/T | **57/26** | **0.0004** | -0.19 |
| improvement | share of the objective improvement | 54/25 | 0.0007 | -0.20 |
| primal_combo | 0.5 improvement + 0.5 late + 0.1 if it found the first solution | 55/25 | 0.0006 | -0.15 |
| primal_v4 | improvement + late, learned name prior for workers with no solution | 56/27 | 0.001 | -0.20 |
| learned | frozen ridge weights on ten features | 56/28 | 0.0015 | -0.20 |
| primal_v2 | the above plus *count* of improvements and last-rank | 52/35 | 0.04 | +0.04 |
| n_solutions | number of solutions (seed 0 only) | 24/21 | n.s. | +0.40 |
| name_prior | fixed order learned from the solo runs (seed 0 only) | 13/20 | n.s. | +0.02 |

* All magnitude-based metrics are statistically indistinguishable from each other and
  beat the default order at every n from 2 to 6 (about 2:1 wins); at n = 7 the two
  portfolios share five of six names and the effect vanishes.
* The mean gain is dominated by cvrp/A-n80-k10, where the seed-1 default runs are
  catastrophic (`default_lp` alone finds no solution in 10 s). Without that instance the
  win rate for `late` is still 51/25 (p = 0.002) but the mean dPI is only about -0.02:
  **the typical gain is small; the win rate is the robust statistic.**
* Consistent wins: job shop ta61 (6/2), knapsack (9/1 and 8/2, tiny absolute gains), golomb
  (7/1), strip packing (5/2), qap (4/1). Losses: set covering (2/6), where the late
  improvements come from LNS and the metric promotes `quick_restart` over `max_lp_sym`.
  Coin flips: swv06, edata_la21, cvrp/A-n46-k7.

## 4. What did not work, and why

* **Counting solutions or improvements** (n_solutions, count, late_count, mixed,
  primal_v2). On cvrp, `quick_restart` produces 5-14 tiny improvements late in the run
  (1-4 % of the total objective improvement) while `default_lp` makes the two big early
  jumps (90 %). The count metrics rank `quick_restart` first; alone it is three times worse.
  On knapsack, `core` emits 20 solutions in the first 20 ms and is then useless. Polishing in
  small steps is what the LNS pool does anyway; the primal integral is decided by who made
  the big jumps.
* **Leave-one-out ablation** as ground truth or as a "blacklist" verification: within noise
  at 10 s (see section 2).
* **A fixed, name-only order** learned from the solo data (`default_lp > fixed >
  quick_restart > no_lp ~ max_lp > core > reduced_costs`): no better than CP-SAT's default
  order. The log at hand carries the information, not the name.
* **Adding the proving side** (objective-bound and shared-bound counts, primal_bound):
  lowers the correlation with the solo order (0.57), as expected for a primal target.
* **Learning weights** (ridge, leave-one-instance-out): does not beat the one-line metric
  with 12 instances; the fitted weights confirm the picture (magnitude share +1.06, late
  count +0.37, last-rank +0.60, conflicts -0.50, bound-only workers -0.30, count -0.03).

## 5. Recommendation

Use **`late`** as the importance score of a full subsolver s in a log with time limit T:

    score(s) = sum over improving solutions found by s of |delta_obj| * (t / T)
               / sum over all improving solutions of |delta_obj|

and sort descending; ties (typically several workers with score 0) keep CP-SAT's default
order. It is one line, explainable ("how much of the objective improvement did this worker
deliver, and how late"), uses only the `#k` solution lines (finder, time, objective), and was
the best of 15 candidates in the verification. Three readings of a zero score need care:
a worker with no solution may be *shadowed* by a faster sibling that found the same
solutions first (`max_lp` on several instances is a fine solo worker with zero solutions in
the portfolio), so "zero" means "not needed here", not "useless".

For the analyzer's insights: report the top-ranked workers as "carried the objective
search", workers with many `Objective bounds` entries and no solutions as "bound workers",
and treat the rest as "shadowed / not needed at this size".

## 6. Second session (2026-09-28): strategies to always keep, and the follow-ups

**Is there a strategy to always keep?** Three independent views on the existing and new data:

* *Solo robustness* (2 workers, 3 seeds): `default_lp` is the only name that is never bad
  alone: mean rank 2.25 of 6, worst result 1.66x the best, mean regret 0.06. Every other
  name has a catastrophe somewhere (no_lp 17x on cvrp, core 16x, reduced_costs 4.9x,
  max_lp 3.0x, quick_restart 2.9x). `fixed` (only on models with a search strategy) is
  second: worst 1.85x.
* *Value of inclusion* (ridge on membership differences over 211 ranked-vs-default pairs):
  removing `default_lp` costs +0.52 relative primal integral; swapping `core` in costs
  +0.60 (it pays only on qap); `quick_restart` +0.12; no_lp, fixed, max_lp small gains.
* *All 15 pairs at 3 workers* (360 runs, seeds 0+1): `fixed` is in the best pair on all
  four models that have it, `default_lp` on 5 of 12; the best pair changes per class
  (fixed+no_lp on ta61, no_lp+reduced_costs on knapsack and golomb, core+max_lp on gap,
  quick_restart+reduced_costs on qap). Mixed LP levels beat same-level pairs on average
  (z -0.08 vs +0.26), so complementarity exists.

Consequences, tested:

| rule (top-2 at F = 2, 24 picks) | mean regret vs best pair | max regret |
|---|---|---|
| `late` | 0.037 | 0.10 |
| `default_lp` pinned + late | 0.038 | 0.10 |
| `default_lp` + `fixed` pinned | 0.042 (6 exact hits, the most) | 0.17 |
| CP-SAT default order | 0.196 | 1.85 |
| forced LP/no-LP mix | 0.292 | 4.29 |

The log signal beats every structural rule; enforcing diversity is harmful (on cvrp it pairs
default_lp with a no-LP worker that is four times worse). Pinning default_lp (`late_anchor`)
changes little in the full protocol (43 wins / 21 losses vs 57/26 for plain `late`) because
`late` keeps default_lp in its top set by itself. Recommendation for the analyzer: never
label `default_lp` or `fixed` as useless; when their score is low, call them the backbone.

**Blacklist direction** (ignore the most vs the least important default name at n = 4, 6,
CP-SAT refills the slot): removing the top name hurts more than removing the bottom one in
35 of 46 pairs (p = 0.0003). Against the default itself, removing the least important is a
coin flip (16/19): the refill (quick_restart / reduced_costs) is no better. The metric says
what to keep; dropping buys nothing.

**12-worker logs** (8 full subsolvers): negative. `late` read from a 12-worker log gives
53 wins / 52 losses; its Spearman against the solo ground truth falls from 0.69 to 0.44.
Crowded portfolios attribute improvements to `quick_restart_no_lp`, `pseudo_costs` and
`max_lp`, and selections containing them lose. A default-order prior does not repair it.

**30 s runs** (six instances, n = 2, 4, 6): a weak trend only, 19 wins / 13 losses
(p = 0.19). Wins persist on job shop, knapsack and set covering; cvrp flips. The longer the
run, the more of the late improvement comes from the LNS pool, and the less the choice of
full subsolvers matters.

## 7. Third session (2026-09-28): the LNS pool

Question: does the log also say which *interleaved* workers (LNS neighborhoods, `ls`) to keep,
and can we "add more of what works"? A neighborhood cannot be duplicated in CP-SAT; the
levers are `ignore_subsolvers` (switch names off; verified: the remaining ones get the freed
time, 2.2x the calls) and `num_full_subsolvers` (move threads to the pool: 1.9x the LNS
calls at 4 full instead of 6, 2.7x at 2). All selections were read from the log of a
different seed than the run they were tested on.

**Which neighborhoods: no gain.** Switching off the neighborhoods that were idle in the
log is a coin flip against the default (26/22 at 10 s, 6/6 at 30 s) and against switching
off the same number at random (25/23). Removing the best ones tends to hurt (31/17, p = 0.06),
so the per-neighborhood attribution means something, but the ranking is unstable across
seeds (Spearman 0.59) and CP-SAT's own neighborhood scheduling leaves nothing to gain. Same
lesson as Phase E for the full subsolvers: the log tells what to keep, not what to drop.

**How much LNS: a real lever.** If the LNS/LS pool delivered at least half of the
time-weighted objective improvement in the log, giving it more threads
(`num_full_subsolvers = 4` at 8 workers) beat the default in **18 of 21** paired runs at
10 s (p = 0.001, median primal integral -17%) and in 6 of 7 at 30 s. With a low pool share
it did not help (12/15) and could be catastrophic (strip packing +405%, knapsack +3-30%).
The split at 0.5 was fixed before the runs; the result is monotone in the threshold (0.7:
13 of 13). Gains are consistent per model (jobshop swv06, both cvrp, set covering, qap).

Recommendation for the analyzer: when the "LNS & heuristics" share is high (>= 0.5),
say that this run was carried by LNS and that giving LNS more threads
(`num_full_subsolvers` about half the workers) paid off in these tests; say nothing about
individual neighborhoods.

## 8. Fourth session (2026-09-28): held-out confirmation

Both results were chosen by looking at the same 12 instances, so they were re-tested on
39 instances the study had never used (13 classes, picked by a fixed rule in
`study/holdout.py`: the larger half of every optimization class, kept if the objective still
improves after 3 s and 3 full subsolvers take part, first 4 per class), 4 seeds, 10 s,
with the hypotheses written into PLAN.md before the first run. 1,873 runs.

**`late` ranking (fewer workers): confirmed, stronger than before.** The top-F(n) strategies
by `late` from an 8-worker log beat CP-SAT's default choice in **377 of 536** pairs
(70 %, p ~ 1e-20; before: 57/26), at every worker count (2: 74/29, 3: 118/36, 4: 99/43,
6: 86/51), median primal integral -11 %. Per instance 27 better / 12 worse (p = 0.024).
Strong on routing, assignment, covering, flexible jobshop, knapsack; a coin flip on classic
jobshop, graph coloring, golomb; no class significantly worse.

**More LNS threads: confirmed.** When the LNS pool delivered >= 0.5 of the time-weighted
improvement in the log of a different seed, `num_full_subsolvers=4` at 8 workers beat the
default in **53 of 67** pairs (p < 1e-5, median -28 %; per instance 14/4, p = 0.03). Below
0.5 it was about neutral (52/37, median -5 %), with a few large losses (up to +166 %). At
12 workers, `num_full_subsolvers=6` still helps above 0.5 (27/12, p = 0.02, median -15 %),
but less, and not significantly per instance.

**Part 2 (the night after): the reliability limits.** The two limits that the analyzer's
card warned about came from the 12 development instances and did not survive the larger
test (another 1,647 runs, same 39 instances, pre-registered):
* Ranking read from a **12-worker** log (8 full strategies): **363 better / 189 worse**,
  29 of 39 instances (the development set had suggested a coin flip, 53/52).
* **30 s** runs (log and test runs at 30 s): **249 better / 126 worse**, 30 of 39 instances,
  median -11 % (the development set had suggested a fade, 19/13).
* More LNS threads in **30 s** runs with LNS share >= 0.5: **42 better / 22 worse**
  (p = 0.017), median -13 %: still a gain, half the size of the 10 s one.
Lesson: with 12 instances and 2 seeds, "not significant" meant "too few runs", twice.

What changes for the analyzer: the fewer-workers suggestion stands as is; its two caveats
now only mark the edge of the tested range (more than 8 full strategies, runs over 30 s). The LNS hint is
now well supported: "LNS delivered >= half of the progress: try num_full_subsolvers = half
the workers; expect about -25 % primal integral at 8 workers, less at 12".

## 9. Caveats

* The metric is a short-run instrument for moderate portfolios: verified for 10 s logs
  with about six full subsolvers (8 workers). At 12 workers it is a coin flip, at 30 s a
  weak trend. CP-SAT 9.15, 12 instances.
* Run-to-run variance on cvrp is large (same-set pairs differ by up to 2.85 PI); results
  on that class should be read as win/loss only.
* Knapsack and gap differences are real in sign but tiny in size (gaps around 0.001).

## 10. How to reproduce

    cd benchmarks
    uv run python -m portfolio_study.experiments.exp_a_screen              # 8-worker logs, seeds 0,1
    uv run python -m portfolio_study.experiments.exp_b_ablation 0           # solo + LOO ground truth
    uv run python -m portfolio_study.experiments.exp_b_ablation --solo-only 1 2
    uv run python -m portfolio_study.experiments.exp_b_report 0 1 2         # Spearman vs ground truth
    uv run python -m portfolio_study.experiments.exp_c_verify --metrics late,improvement 0 1
    uv run python -m portfolio_study.experiments.exp_c_report -v 0 1        # W/L tables
    uv run python -m portfolio_study.experiments.exp_d_pairs 0 1            # all pairs at 3 workers
    uv run python -m portfolio_study.experiments.exp_d_pairs --report 0 1
    uv run python -m portfolio_study.experiments.exp_d_rules                # pair-selection rules
    uv run python -m portfolio_study.experiments.exp_e_blacklist 0 1        # remove best vs worst
    uv run python -m portfolio_study.experiments.exp_e_blacklist --report 0 1
    uv run python -m portfolio_study.experiments.exp_c_verify --metrics late --base 12 --workers 2,3,4,6,8 0 1
    uv run python -m portfolio_study.experiments.exp_c_verify --metrics late --time 30 --workers 2,4,6 --only ta61,nug15 0 1
    uv run python -m portfolio_study.experiments.exp_g_lns 0 1 2 3          # LNS pool, 10 s (~80 min)
    uv run python -m portfolio_study.experiments.exp_g_lns --report -v 0 1 2 3
    uv run python -m portfolio_study.experiments.exp_g_lns --time 30 0 1    # 30 s, six instances
    for s in screen select base late lns report; do                         # held-out (~3 h)
      uv run python -m portfolio_study.experiments.exp_h_holdout $s; done
    for s in late12 long; do                                                # part 2 (~5 h)
      uv run python -m portfolio_study.experiments.exp_h_holdout $s; done
    uv run python -m portfolio_study.experiments.exp_h_holdout report --part2
    uv run --with pytest pytest portfolio_study/tests -q                    # 12 tests

Runs are cached under `runs/<problem>/<instance>/` and reused across metrics whenever the
whitelisted set is the same. A full re-run of everything takes about thirteen hours on 12 cores.

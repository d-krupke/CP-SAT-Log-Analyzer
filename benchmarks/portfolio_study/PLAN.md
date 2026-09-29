# Portfolio-importance study

Created 2026-09-27. Goal: from a *single* CP-SAT log, rank the full-problem subsolvers
(`default_lp`, `no_lp`, `fixed`, `max_lp`, `quick_restart`, `reduced_costs`, `core`, ...)
by how much they matter for the **objective search**, and verify the ranking with
reduced-worker runs. "Metric" is loose: a scoring, an ordering, or a probability that
removing a subsolver hurts.

## Facts that shape the design (CP-SAT 9.15, `cp_model_search.cc`)

- Default order: default_lp, fixed, core, no_lp, max_lp(_sym), quick_restart, reduced_costs,
  quick_restart_no_lp, pseudo_costs, lb_tree_search, probing, objective_lb_search, ...
  Names that do not apply (fixed without scheduling/strategy, core with one objective term)
  are dropped, then the list is truncated to F(n) entries.
- F(n) full subsolvers for n workers: 1, 1, 2, 3, 3, 4, 5, 6 for n = 1..8; 8 for n = 12.
  The other threads run the first-solution workers (until a solution exists) and then the
  interleaved LNS/LS pool. With n = 2 there is one full subsolver and one LNS thread.
- `subsolvers: [...]` (whitelist) replaces the default list, same filtering, same truncation;
  fewer names than F(n) get padded by repeating the first one. `ignore_subsolvers` (globs)
  removes names from either list and also works on LNS/LS names.
- So: at n workers, "default" = first F(n) applicable names; "ranked" = top F(n) names by the
  metric, passed as `subsolvers`. Same thread split, only the choice differs. Fair.
- n = 1 does not use the portfolio path at all: not part of the comparison.
- Machine: 12 physical cores. Runs are packed so that the running worker sum stays <= 12.
- Warning (from the task): most of a run is often spent on the bound, not on the objective.
  All performance measures here are primal-only (objective at time t), and the instance
  screen keeps only instances that still improve the objective well into the run.

## Performance measures (primal only)

For one run with time limit T and best-known objective z* (min over all runs on the instance):
- primal gap g(t) = (z(t) - z*) / max(|z*|, 1), with g = 1 before the first solution
  (for maximization the sign flips);
- final gap g(T);
- primal integral PI = integral of g(t) over [0, T] (rewards early and steady progress);
- first-solution time.
Comparisons are paired (same instance, same n, same seed) and aggregated as win/loss counts
and mean differences over instances, since 10 s multi-thread runs are noisy.

## Questions / experiments

- Q0 (done, empirically verified): how are workers allocated, does the whitelist behave.
- Q1 screening (`exp_a_screen`): 16 candidates, 8 workers, 10 s, 2 seeds. Keep instances
  where the objective still improves after 3 s and where full subsolvers find solutions.
  Also gives the run-to-run noise level.
- Q2 ground truth by ablation (`exp_b_ablation`): for each kept instance and each full
  subsolver X of the 8-worker run:
  (a) leave-one-out: 7 workers, `subsolvers` = the other five (F(7) = 5);
  (b) solo: 2 workers, `subsolvers` = [X] (F(2) = 1, plus one LNS thread).
  Degradation in (a) and quality in (b) are the two ground-truth importance signals.
  Also tells how much the choice matters at all per instance.
- Q3 signals vs ground truth: extract per-subsolver signals from the 8-worker log
  (solutions found, improvement share, late improvements, best rank, bound improvements,
  shared bounds, conflicts, #Done, first solution, default position) and correlate them
  with the ablation ranks. Pick the signals with predictive value.
- Q4 metric candidates (`metrics.py`), each a function log -> ordering:
  M0 default order (baseline), M1 solution count, M2 improvement share,
  M3 time-weighted improvement share, M4 combined primal score, M5 primal + bound
  contribution, M6 data-fitted weights from Q3, ... (extended as the study goes).
- Q5 verification (`exp_c_verify`): for each kept instance, n in {2, 3, 4, 6, 7}
  (F = 1, 2, 3, 4, 5): default vs top-F of each metric, seeds 0 and 1. Runs are cached by
  the *set* of names, so metrics that agree on the top-F share runs.
  Success = the ranked variant has lower final gap / primal integral than default in the
  majority of (instance, n) pairs and never much worse on average.
- Q6 (if time): blacklist direction (drop the least important one at 8 workers and give the
  thread to LNS), LNS-neighborhood importance from `LNS stats`, longer time limits (30 s),
  robustness to the worker count of the normal run (12 workers -> 8 full subsolvers).

## Results log

(appended as the study progresses)

### 2026-09-27 Phase A (screen), 16 instances x 8 workers x 10 s x 2 seeds

- Kept 12 instances (see `candidates.PHASE_B`). Dropped four with one or two solutions or
  a search that is over after 1-3 s.
- Seed-to-seed noise of the final objective: 0-3 % on most instances, 13 % on cvrp/A-n80-k10.
  Paired comparisons with several seeds are necessary; single runs prove nothing.
- Most of the *relative* improvement happens in the first second (first solutions are bad),
  so a magnitude-weighted "late share" is tiny everywhere. The late phase is dominated by
  LNS/LS on cvrp, gap, set_covering and qap; on job shop, mknapsack, golomb and strip packing
  the full subsolvers keep finding solutions.
- Per instance a different full subsolver dominates: no_lp (job shop, golomb, strip packing),
  default_lp (cvrp, set covering, gap), reduced_costs (mknapsack), fixed/quick_restart
  (flexible job shop), core (qap). This is what a metric has to pick up.

### 2026-09-27 Phase B (ablation), 12 instances, 10 s

Runs: leave-one-out at 7 workers (seed 0) and solo at 2 workers (seeds 0-2), 336 runs.

- **Leave-one-out is within noise.** Removing any one of six full subsolvers changes the
  primal integral by less than the seed-to-seed noise on 10 of 12 instances (e.g. mknapsack
  0.04 for every variant, gap 0.11-0.13, qap 2.47-2.52). Redundancy plus the LNS pool hides
  a single removal at 10 s. No metric correlates with the LOO ordering (all |rho| < 0.15).
  Consequence: the "blacklist one" direction is not measurable at this budget; the study
  uses the *solo* result (that subsolver plus one LNS thread) as ground truth.
- **Solo results differ a lot** (cvrp/A-n46-k7: default_lp 1.30 vs max_lp 3.95; gap:
  max_lp 0.13 vs core/no_lp 0.78; mknapsack: reduced_costs 0.03 vs no_lp 0.59) and the
  best solo subsolver changes per instance: no_lp (job shop, golomb, strip packing),
  default_lp (cvrp, set covering, flexible job shop), reduced_costs (mknapsack), max_lp (gap),
  core (qap, tiny margin).
- Spearman of the metric orderings against the solo ordering, mean over 12 instances:
  primal_v2 0.69, late 0.69, late_count 0.67, mixed 0.66, primal_combo 0.65, n_solutions
  0.63, last_rank 0.62, improvement 0.61, primal_bound 0.57, default order 0.27, activity
  (conflicts) 0.23. Ridge regression on ten normalized features, leave-one-instance-out:
  0.67 -> the hand-made weights are as good as fitted ones with 12 instances.
- Stability of an ordering between the seed-0 and seed-1 normal runs: 0.67-0.86 (the
  improvement-magnitude share is the most stable signal, 0.86).
- Surprises worth keeping: (1) `reduced_costs` is the worst solo worker on 10 of 12
  instances but the best on both mknapsack instances; (2) `max_lp` often finds no solution in
  the portfolio yet is a fine solo worker (shadowed by faster siblings), so "zero solutions"
  must not be read as "useless"; (3) pure bound workers (many `Objective bounds` entries,
  no solutions) are the reliable losers for the primal side; (4) the Solutions table `Rank`
  is chronological (0 = the first solution), so a high last rank means "still finding
  solutions late" and is a useful signal; (5) a name-only prior learned from the data
  (default_lp > fixed > quick_restart > no_lp ~ max_lp > core > reduced_costs) is a
  baseline the log-based metrics must beat in Phase C.

### 2026-09-27 Phase C (verification), seed 0, 12 instances, n in {2,3,4,6,7}, 10 s

Protocol: default at n workers vs `subsolvers = top-F(n)` of the metric computed from the
8-worker log of the same seed. Pairs whose top-F *set* equals the default set are pure
timing noise (mean |dPI| 0.04-0.09, reported separately). Runs are reused across metrics
when the name set is the same (order does not matter to CP-SAT).

Wins/losses on the primal integral (negative mean = ranked portfolio better):

| metric | W/L | mean dPI | note |
|---|---|---|---|
| primal_v2 | 23/24 | +0.32 | ranks quick_restart first on cvrp (5 improvements of 1 % total); alone it is 3x worse |
| n_solutions | 24/21 | +0.40 | same failure; also core first on mknapsack (20 tiny solutions at t=0.02) |
| mixed | 23/19 | +0.36 | same |
| name_prior | 13/20 | +0.02 | fixed order is not better than the default order |
| late | 27/16 | -0.02 | magnitude x time |
| primal_combo | 23/15 | -0.02 | 0.5 magnitude + 0.5 late share |
| improvement | 22/13 | -0.02 | magnitude only |
| learned | 23/13 | -0.02 | frozen ridge weights |
| primal_v4 | 23/18 | -0.02 | magnitude + late, name prior for shadowed workers |

Lesson: **count-based signals are harmful**, magnitude-based ones help modestly and
consistently at every n. Counting improvements rewards the subsolver that polishes in tiny
steps (what LNS does anyway); the primal integral is decided by the few big early jumps, and
the worker that made them is the one worth keeping. Wins are ~60 % with mean gains at the
noise level, so a second seed is needed (running).

### 2026-09-27 Phase C, seeds 0+1 (final)

Two seeds, 12 instances, n in {2,3,4,6,7}; ~83 informative pairs per metric (37-41 pairs
had the same set as the default and serve as noise: mean |dPI| 0.12-0.15, dominated by
cvrp/A-n80-k10 where even same-set pairs differ by up to 2.85).

| metric | PI W/L | one-sided sign test | mean dPI | gap W/T/L |
|---|---|---|---|---|
| late (time-weighted magnitude share) | 57/26 | p = 0.0004 | -0.19 | 42/13/28 |
| primal_v4 (magnitude + late + prior for shadowed) | 56/27 | p = 0.001 | -0.20 | 39/13/31 |
| learned (ridge weights) | 56/28 | p = 0.0015 | -0.20 | 39/18/27 |
| improvement (magnitude share) | 54/25 | p = 0.0007 | -0.20 | 41/11/27 |
| primal_combo | 55/25 | p = 0.0006 | -0.15 | 41/12/27 |
| primal_v2 (with counts) | 52/35 | p = 0.04 | +0.04 | 40/10/37 |

Without cvrp/A-n80-k10 (seed-1 default runs there are catastrophic: default_lp alone finds
no solution in 10 s, PI 10.0 vs 5.7 for quick_restart) `late` is still 51/25, p = 0.002; the
mean dPI shrinks to about -0.02, i.e. the typical gain is small and the win rate is the
robust statistic. The gain is present at every n from 2 to 6 and vanishes at n = 7 (F = 5
of 6 names: the two portfolios almost coincide). Per instance: consistent wins on
jobshop/ta61 (6/2), mknapsack (9/1, 8/2; tiny absolute gains), golomb (7/1), strip packing
(5/2), qap (4/1); losses on set covering (2/6, where the LNS does the late work and the metric
picks quick_restart over max_lp_sym) and coin flips on swv06, edata_la21, cvrp/A-n46-k7.

Decision: the metric of record is **`late`** (share of the time-weighted objective
improvement); `improvement`, `primal_combo`, `primal_v4` and `learned` are statistically
indistinguishable from it, and anything that counts solutions is worse than the default order.

## Phase D-F: "always keep" strategies and follow-ups (2026-09-27, second session)

Questions:
- Q7 Is there a strategy that should always be kept? Evidence: worst-case solo regret per
  name (Phase B data), value-of-inclusion regression on the Phase C pairs, and an all-pairs
  experiment at 3 workers (F = 2) that also shows complementarity (LP vs no-LP partners).
- Q8 Does pinning that strategy (`late_anchor`) improve on `late` in the Phase C protocol?
- Q9 Blacklist direction as a paired contrast: at n = 4, 6, ignore the most vs the least
  important default name (CP-SAT refills the slot). Removing the best must hurt more.
- Q10 Does the metric read from a 12-worker log (8 full subsolvers) still work, and does the
  ordering agree with the 8-worker one?
- Q11 Does the effect survive 30 s runs (six instances, n = 2, 4, 6)?

### Offline results (existing runs)

Solo robustness (2 workers, 3 seeds, 12 instances): default_lp is never bad alone (mean rank
2.25 of 6, worst PI 1.66x the best, mean regret 0.06). Everything else has a catastrophe:
no_lp up to 17x (cvrp), core 16x (cvrp), reduced_costs 4.9x, max_lp 3.0x, quick_restart 2.9x.

Value of inclusion (ridge on membership differences, 211 ranked-vs-default pairs, relative
dPI): removing default_lp costs +0.52; including core instead of a default name costs
+0.60 (helps only on qap); quick_restart +0.12 (swapped in 98 times, rarely worth it);
no_lp -0.11, fixed -0.07, max_lp -0.03 slightly positive contributions; reduced_costs neutral.

### Phase D: all pairs at 3 workers (F = 2), seeds 0+1, 360 runs (51 reused)

- Best pair per instance: default_lp+fixed (swv06, edata_la21), fixed+no_lp (ta61),
  default_lp+no_lp (A-n46-k7), default_lp+quick_restart (A-n80-k10), no_lp+reduced_costs
  (mknapcb5, golomb), max_lp+quick_restart (mknapcb6), default_lp+max_lp_sym (set covering),
  fixed+reduced_costs (strip packing), core+max_lp (gap), quick_restart+reduced_costs (qap).
- Membership in the best pair: default_lp 5/12, **fixed 4/4 of the models that have it**,
  no_lp 4, reduced_costs 4, quick_restart 3, max_lp 2(+1 sym), core 1. Mean z-scored PI of
  the pairs containing a name: default_lp -0.42, fixed -0.23, no_lp -0.05, quick_restart
  -0.01, max_lp +0.16, core +0.24, reduced_costs +0.29 (a good *specialist*, a bad partner).
- Complementarity exists on average: pairs with different LP levels z = -0.08 (n=140) vs
  same level +0.26 (n=40), driven by the "two bound workers" pairs being bad.
- But as a *selection rule* it fails (exp_d_rules, regret vs the best pair over 24 picks):
  `late` top-2 mean regret 0.037 (max 0.10), anchor(default_lp)+late 0.038, anchor with
  fixed 0.042 (but 6 exact hits, the most), default 0.196 (max 1.85), forced LP-diverse
  0.29 (max 4.29: on cvrp it pairs default_lp with a no-LP worker that is 4x worse).
  Conclusion: the log signal beats every structural rule; forcing diversity is harmful;
  pinning default_lp changes nothing at F = 2 because `late` already keeps it. `fixed` is
  the one strategy that is always in the best pair when it exists; the default order already
  puts it second, so the only actionable rule is "do not drop `fixed` on scheduling models".

### Phase E: blacklist contrast (ignore the best vs the worst default name by `late`), n = 4, 6, seeds 0+1

Removing the most important name hurts more than removing the least important one in
**35 of 46 pairs** (sign test p = 0.0003; mean difference +0.38 PI at n = 4, +0.29 at
n = 6). Largest effects on cvrp (dropping default_lp: +1.3 to +4.3), qap (dropping core
+0.2), ta61 (dropping no_lp +0.1 to +0.2). Knapsack and gap are flat (everything within
0.01). So the metric's ordering is meaningful in the blacklist direction too, and the
earlier "leave-one-out is noise" finding was a matter of statistical power: single
removals of *arbitrary* names are noise, the removal of the top-ranked one is not.
Against the default itself: remove-best is worse in 26 of 35 pairs, remove-worst is a coin
flip (16 better / 19 worse, mean -0.01). Blacklisting the least important name gains nothing
because CP-SAT refills the slot with the next default name (quick_restart / reduced_costs),
which is no better. The metric tells what to *keep*; there is no free lunch in dropping.

### Phase F1: metric read from a 12-worker log (8 full subsolvers), verified at n = 2, 3, 4, 6, 8

**Negative result.** `late` from the 12-worker log: 53 wins / 52 losses on the primal
integral (105 pairs, seeds 0+1), Spearman against the solo ground truth drops from 0.69
(8-worker log) to 0.44; the 8w and 12w orderings agree only at rho = 0.75. The crowded
portfolio attributes improvements to `quick_restart_no_lp` and `pseudo_costs` (8th/9th
default names, only present from 12 workers) and to `max_lp`; selections containing them
lose (max_lp +0.16 mean dPI, pseudo_costs +0.06, quick_restart_no_lp 28 wins of 65). With
eight near-duplicate searches the "who reported the solution first" attribution becomes
random. Consequence: the metric is reliable for logs with ~6 full subsolvers (8 workers);
for bigger portfolios it needs a prior (tested next: `late` + lambda * default-order prior).
Prior test (offline, Spearman vs solo): adding lambda * default-order position to `late`
only lowers the correlation, on both log sizes (8w: 0.65 -> 0.57 at lambda 0.3; 12w: 0.50 ->
0.42). The 12-worker problem is not a missing prior; the attribution itself is noisier.
Not pursued further; documented as a limitation.

### Phase F2: 30 s runs, six instances (ta61, A-n46-k7, mknapcb5_00, order12, scpcyc09, nug15), n = 2, 4, 6, seeds 0+1

`late` from the 8-worker 30 s log: 19 wins / 13 losses on the primal integral (p = 0.19,
not significant), mean dPI +0.06 driven by cvrp/A-n46-k7 (1/4). Wins persist on ta61 (4/2),
knapsack (5/1) and set covering (5/1). The effect fades with the time limit, as expected:
the longer the run, the larger the share of the late improvements that come from the LNS
pool rather than from the full subsolvers, and the less the choice of full subsolvers
matters. The metric is a *short-run* instrument.

### Conclusions of the second session

1. "Always keep": `default_lp` is the only strategy that is never bad alone and whose
   removal reliably costs; `fixed` is in the best pair on every model that has one. Both are
   already the first two names in CP-SAT's default order, and `late` keeps default_lp in its
   top set on its own, so pinning them (`late_anchor`) changes almost nothing (43/21 vs
   57/26 wins, fewer deviations from default). Recommendation for the analyzer: never
   report default_lp or fixed as "useless"; report them as "backbone" when they have a low
   score.
2. Complementarity is real on average (mixed LP levels beat same-level pairs) but every
   structural rule that enforces it loses to the log signal, badly on cvrp. Do not enforce.
3. The blacklist direction is measurable as a contrast (35/46) but offers no gain over the
   default: CP-SAT refills the slot with an equally mediocre name.
4. Limits: the metric needs a log with a moderate portfolio (~6 full subsolvers, 8
   workers) and a short time limit; with 12 workers or 30 s the win rate drops to a coin
   flip or a weak trend.

## Phase G: the LNS/LS pool (2026-09-28, third session)

Question (from the analyzer integration): can the log also say which *interleaved* workers
(LNS neighborhoods, `ls`, `feasibility_pump`) matter, and does acting on it help? A
neighborhood cannot be duplicated; the two levers are `ignore_subsolvers` (switch names off,
the rest get their time) and `num_full_subsolvers` (move threads from full subsolvers to the
pool). Code: `study/lns.py` (signals, pruning rules, tested in `tests/test_lns.py`),
`experiments/exp_g_lns.py` (runs + report).

Signals per pool name: time-weighted improvement share (as `late`; `ls_*`/`fj_*` finder
names folded into `ls`/`fj`) and, as tie-breaker, the local improvement rate `Improv/Calls`
from the LNS stats table. At 8 workers / 10 s the pool gets ~2 threads and each
neighborhood only 4-16 calls, so most neighborhoods have no global improvement.

### G0 mechanism check (ta61, seed 9, 8 workers, 10 s)

| arm | full | LNS calls per neighborhood | final objective |
|---|---|---|---|
| default | 6 | 8.6 | 3098 |
| ignore 6 of 13 pool names | 6 | 18.9 | 3091 |
| num_full_subsolvers = 4 | 4 | 16 | 3094 |
| num_full_subsolvers = 2 | 2 | 23.3 | 3053 |

`ignore_subsolvers` accepts `rins/rens`, `ls`, `feasibility_pump`; freed time goes to the
remaining names (not just to idle threads); fewer full subsolvers add `ls_lin` to the pool.

### G1 offline: cross-seed stability of the pool ranking (seed 0 vs 1 default logs)

Mean Spearman 0.59 (0.07 nug15 ... 0.93 set covering), kept-set Jaccard 0.59, same top-1 on
4 of 12. Much less stable than the full-subsolver ranking. The pool's share of the total
improvement also swings between seeds (A-n80-k10 0.36 vs 0.96, order12 0.53 vs 0.00);
knapsack pools never improve the global best in 10 s (share 0, ranking by rate only).
Expectation before the runs: pruning gains, if any, will be small and noisy.

### G2 design

8 workers, paired with the default run of the same instance and seed; selection read from
the default log of the partner seed (0<->1, 2<->3), i.e. out of sample.
Arms: `prune` (ignore every pool name without share, keep >= 4), `random` (same number at
random: control for "fewer names"), `top` (same number of the best names: contrast),
`nf4`, `nf2` (more LNS threads). 10 s: 12 instances x seeds 0-3; 30 s: the six Phase F2
instances x seeds 0-1. Measure: primal integral, sign tests; nf arms also split by the
reference log's pool share (>= 0.5) to test "give LNS more threads when it carried the run".

### G2 results (2026-09-28; 288 runs at 10 s, 72 at 30 s)

Relative primal-integral difference (arm - default) / default, "better" = lower PI.

| arm | 10 s (48 pairs) | 30 s (12 pairs) |
|---|---|---|
| prune idle names | 26 better / 22 worse, p = 0.67 | 6 / 6 |
| random pruning (control) | 25 / 23, p = 0.89 | 9 / 3, p = 0.15 |
| prune the best names (contrast) | 17 / 31, p = 0.06, median +3.5% | 6 / 6 |
| prune vs random | 25 / 23 | 3 / 9 |
| prune vs top | 31 / 17, p = 0.06 | 8 / 4 |
| nf4, all | 30 / 18, p = 0.11 | 7 / 5 |
| **nf4, reference pool share >= 0.5** | **18 / 3, p = 0.001, median -17%** | 6 / 1 |
| nf4, pool share < 0.5 | 12 / 15, median +1.7% | 1 / 4 |
| nf2, pool share >= 0.5 | 17 / 4, p = 0.007, median -14% | 5 / 2 |
| nf2, pool share < 0.5 | 8 / 19, p = 0.05, mean +34% | 1 / 4 |

The 0.5 split was fixed in the design above before the runs. Threshold sensitivity (nf4,
10 s, high side): 0.3: 21/8, 0.4: 19/6, 0.5: 18/3, 0.6: 14/1, 0.7: 13/0. Monotone, no
cherry-picked cut. Both durations pooled, nf4 at share >= 0.5: 24 better / 4 worse.
Per instance (10 s, nf4): consistent gains of 15-35% PI on swv06, A-n46-k7, A-n80-k10,
scpcyc09 (all seeds), small ones on nug15; consistent losses on both knapsacks (pool share
0: +3% to +30%) and one catastrophe on strip packing c4-p1 (share 0.02: +405% on seed 2,
+572% with nf2). The effect is largely a *model* property that the log reveals.

Conclusions:
1. **Which neighborhoods: no lever.** Pruning the idle names is indistinguishable from the
   default and from random pruning. Removing the best names tends to hurt (31/17 contrast,
   like Phase E for the full subsolvers), so the pool ranking carries some information, but
   there is nothing to gain by acting on it: CP-SAT's own neighborhood scheduling already
   adapts (difficulty, time limits), and the kept set is unstable across seeds (G1).
2. **How many threads for LNS: a real lever.** When the log shows the LNS/LS pool delivered
   at least half of the time-weighted objective improvement, moving threads from full
   subsolvers to the pool (`num_full_subsolvers = 4` at 8 workers) lowered the primal
   integral in 18 of 21 pairs (median -17%), out of sample. When the pool share is low it
   is a coin flip at best and can be catastrophic (knapsack, strip packing). nf4 is the
   safer dose: nf2 gains about as much on the high side and loses more on the low side.
3. Analyzer consequence: the "LNS & heuristics" share of the Portfolio ranking card is an
   actionable signal. Note the analyzer's share also includes first-solution workers (fj);
   the study's pool share does not. They differ little after the first solution.

## Phase H: held-out confirmation of both results (fourth session, 2026-09-28)

Why: every result so far comes from the same 12 instances (Phase B list), 2-4 seeds; the
`late` metric and the LNS 0.5 split were chosen by looking at them. Phase H re-tests both on
instances the study never used, with the analysis fixed here before the first run.

Instances (mechanical, `study/holdout.py`, recorded in `holdout.json`): the larger half of
every optimization class (16 classes, 188 candidates, Phase A excluded), one default run
(8 workers, 10 s, seed 0) each, kept if the objective still improves after 3 s and at least
3 full subsolvers found a solution or a bound; the first 4 per class in list order.
Seeds 0-3, 10 s, `experiments/exp_h_holdout.py`.

Hypotheses and tests (two-sided exact sign test on paired primal integrals, alpha 0.05):
- **H1** (`late`, Phase C protocol): at n in {2,3,4,6}, top-F(n) by `late` from the 8-worker
  log of the same seed has a lower PI than the default in more pairs than it has a higher one.
  Pairs where the two sets coincide are skipped. Prior: Phase C 57/26.
- **H2** (LNS, Phase G protocol): at 8 workers, `num_full_subsolvers=4` vs default, reference
  = default log of the partner seed. Primary: pairs with pool share >= 0.5 win (p < 0.05).
  Secondary: pairs below 0.5 do not win; threshold curve 0.3-0.7; per class.
- **H2b**: same at 12 workers with `num_full_subsolvers=6` (half), seeds 0, 1.
Not decided in advance: nothing else. Anything reported beyond these is exploratory.

### Phase H results (2026-09-28, 1,873 runs, `expH_report.txt`)

Selection: 188 screened, 61 passed, 39 selected from 13 classes (binpacking, bin_packing_2d
and qap had no instance with a late improvement). Run log: `expH_part1.log` (screen to late)
and `expH.log` (lns). The detached chain was killed from outside after the late stage
(no OOM, no error; the stage re-runs cleanly from cache); the lns stage was restarted as
a systemd user unit and finished.

**H1 confirmed.** late top-F(n) vs default, PI: 377 better / 159 worse (p ~ 1e-20),
median relative dPI -10.6% (5%-trimmed mean -9.5%; the plain mean -1.8% is pulled by
relative losses on runs whose PI is already near 0). n=2 74/29, n=3 118/36, n=4 99/43,
n=6 86/51 (p = 0.004). Per instance (mean dPI): 27 better / 12 worse, p = 0.024.
Per class: clear wins on tsp 37/12, cvrp 38/13, gap 42/2, dominating_set 14/2,
flexible_jobshop 49/15, set_covering 36/16, mknapsack 43/13; coin flips on jobshop 32/28,
graph_coloring 3/3, golomb 4/8; no class significantly worse. Worst real case:
tsp/si175 n=2 (PI 2.1 -> 7.0).

**H2 confirmed.** nf4 vs default at 8 workers, relative PI:
| pool share | better / worse | p | median |
|---|---|---|---|
| all | 105 / 51 | <1e-4 | -9.7% |
| >= 0.5 (primary) | **53 / 14** | **<1e-5** | **-27.8%** |
| < 0.5 | 52 / 37 | 0.14 | -4.6% |
Threshold curve (>= side): 0.3 66/17, 0.4 62/16, 0.6 45/10, 0.7 33/6, all median -26 to
-30%. Per instance with mean share >= 0.5: 14 / 4 (p = 0.031); below: 12 / 9. High-share
wins by class: set_covering 11/0, max_clique 8/0, flexible_jobshop 5/0, dominating_set 4/0,
graph_coloring 4/0, cvrp 6/2; neutral on jobshop 7/4, rcpsp 5/5, strip_packing 3/3.
Different from Phase G: below 0.5, nf4 did *not* hurt on the held-out set (median -4.6%,
worst cases golomb order11 +110%, rcpsp j1201_1 +166%); the Phase G catastrophes came from
knapsack/strip packing with share ~0.

**H2b partly confirmed.** nf6 vs default at 12 workers, seeds 0-1: share >= 0.5: 27 / 12
(p = 0.024, median -14.5%), below: 21 / 18. Per instance only 13 / 7 (p = 0.26). The effect
halves in size at 12 workers (the default already gives LNS 4 threads there).

Conclusion: both results survive a pre-registered test on 39 unseen instances. The LNS share
is best read as "how much there is to gain": >= 0.5 means about -25% PI at 8 workers; below
it, more LNS threads is roughly neutral with rare large losses.

## Phase H part 2: the card's reliability limits on the held-out set (2026-09-28, night)

Why: the card's two caveats rest on the 12 development instances only: "many full
strategies" (ranking from 12-worker logs was a coin flip, 53/52) and "long run" (30 s:
19/13). Same 39 instances, seeds 0-3, `exp_h_holdout.py` stages `late12` and `long`.
- **H3**: H1 with the ranking read from a 12-worker 10 s log, tested at n in {2,3,4,6}.
  Disclosure: a partial result was seen before this was written: 41/12 on the 53 pairs
  whose runs already existed (12-worker logs of seeds 0,1 from the LNS stage). The full
  result includes these pairs.
- **H4**: H1 at 30 s: ranking from the 8-worker 30 s log, tested at n in {2,4,6} at 30 s.
- **H5**: H2 at 30 s: nf4 vs default at 8 workers, 30 s, split at pool share 0.5.
Tests as in part 1 (two-sided sign test, alpha 0.05, pairs and per instance). Decision for
the card: a caveat stays if its test is not significant in favor of the ranking; the LNS hint
extends to 30 s runs only if H5 is significant at share >= 0.5.

### Phase H part 2 results (2026-09-29, 1,647 runs, `expH2_report.txt`)

Run log: `expH2_part1.log` and `expH2.log`. **All three "kills" of this study (the 1 h abort
in Phase G, the chain after the late stage in Phase H, the first part-2 unit at 22:50) were
`run-or-notify`'s own `timeout=3600` (exit 124)**, not the session or the harness. The
chain now runs without it and mails via `notify-me` itself.

**H3 confirmed (12-worker logs).** 363 better / 189 worse (p ~ 1e-13), per instance 29/10
(p = 0.003), median relative dPI -8.5%; n=2 70/36, n=3 102/50, n=4 102/45, n=6 89/58. The
dev-set "coin flip" (53/52 on 12 instances) does not hold up. Of the 552 pairs, 53 were seen
before pre-registration (41/12); on seeds 2-3 alone, which contain none of them: 180/91.

**H4 confirmed (30 s).** 249 better / 126 worse (p ~ 1e-10), per instance 30/9 (p = 0.001),
median relative dPI -11%; n=2 66/34, n=4 106/34, n=6 77/58 (p = 0.12). The dev-set fade
(19/13 at 30 s) was a lack of power, not a fade.

**H5 confirmed (LNS at 30 s).** nf4 vs default, pool share >= 0.5: 42 / 22 (p = 0.017),
median -13% (10 s: -28%); below 0.5: 43/49, neutral. Threshold curve >= side: 0.3 52/29,
0.4 46/26, 0.6 35/19, 0.7 32/14. The gain shrinks with run length but stays.

Card changes (as pre-registered): `reliable_max_full` 7 -> 8 and `long_run_seconds` 30 ->
35, i.e. the two caveats now mark the edge of the tested range instead of claiming
unreliability; the method texts quote the held-out numbers; the LNS hint quotes 30 s.

## Correction 2026-09-29: pool share with all neighborhood variants

A review of the analyzer found `rins_*`/`rens_*` (pool name `rins/rens`) and
`lb_relax_lns_bool(_h)` (`lb_relax_lns`) missing from the pool share: only `ls_*` was
folded. `study/lns.py` now folds them (same rule as `pool_member` in the analyzer); the
Phase G pruning arms keep the old attribution so they rebuild to the runs that exist.
Re-evaluated from the cache, threshold unchanged at 0.5 (REPORT.md section 8 has the table):
G 10 s 18/3 -> 19/4; H2 53/14 -> 55/14 (per instance 16/5); H2b 27/12 -> 27/13 (p = 0.039);
H5 42/22 -> 45/27 (p = 0.044, median -10%). Below 0.5 still neutral. No decision changes.

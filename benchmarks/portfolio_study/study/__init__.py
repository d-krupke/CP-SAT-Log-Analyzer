"""Portfolio-importance study (created 2026-09-27).

Goal: derive, from a single CP-SAT log, an importance ordering of the full-problem
subsolvers (``default_lp``, ``no_lp``, ``fixed``, ...) and verify it with reduced-worker
runs. See ``../PLAN.md`` for the questions, protocol and results log.

Modules
- ``runner``   solve one (instance, worker count, subsolver set, seed) and store log + meta;
               a small scheduler packs jobs into the 12-core budget.
- ``signals``  per-subsolver signals extracted from a parsed log (cpsat_logutils).
- ``metrics``  candidate importance metrics: signals -> ordered list of subsolver names.
- ``evaluate`` performance of a run (final gap, primal integral) and paired comparisons.
"""

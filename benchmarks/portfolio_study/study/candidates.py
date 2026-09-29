"""Instances of the portfolio study (created 2026-09-27).

Picked from the corpus scan of the 8-worker/60 s logs: optimization instances whose
objective keeps improving well into the run and where several *full* subsolvers found
solutions (so the choice of full subsolvers can matter at a 10 s limit). Diverse
problem classes on purpose. ``PHASE_A`` is the wide screening list; the selection for
the later phases is recorded in PLAN.md after the screening results.
"""

PHASE_A: list[tuple[str, str]] = [
    ("jobshop", "swv06"),
    ("jobshop", "ta61"),
    ("flexible_jobshop", "edata_la21"),
    ("flexible_jobshop", "vdata_abz7"),
    ("rcpsp", "j12053_5"),
    ("cvrp", "A-n46-k7"),
    ("cvrp", "A-n80-k10"),
    ("mknapsack", "mknapcb5_00"),
    ("mknapsack", "mknapcb6_20"),
    ("golomb_ruler", "order12"),
    ("set_covering", "scpcyc09"),
    ("strip_packing", "c4-p1"),
    ("gap", "gapd_05"),
    ("graph_coloring", "DSJC125.5"),
    ("qap", "nug15"),
    ("binpacking", "Falkenauer_u500_00"),
]

# Kept after the Phase A screen (2026-09-27): objective still improving after 3 s and at least
# three full subsolvers with solutions or bounds. Dropped: binpacking/Falkenauer_u500_00 (one
# solution), graph_coloring/DSJC125.5 and rcpsp/j12053_5 (search over after 1-3 s),
# flexible_jobshop/vdata_abz7 (a handful of solutions, all early).
PHASE_B: list[tuple[str, str]] = [
    ("jobshop", "swv06"),
    ("jobshop", "ta61"),
    ("flexible_jobshop", "edata_la21"),
    ("cvrp", "A-n46-k7"),
    ("cvrp", "A-n80-k10"),
    ("mknapsack", "mknapcb5_00"),
    ("mknapsack", "mknapcb6_20"),
    ("golomb_ruler", "order12"),
    ("set_covering", "scpcyc09"),
    ("strip_packing", "c4-p1"),
    ("gap", "gapd_05"),
    ("qap", "nug15"),
]

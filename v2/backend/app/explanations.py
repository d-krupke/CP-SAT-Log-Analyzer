"""Human-readable explanations for log sections, tables, columns and counters.

Written for the v2 analyzer. The texts follow the CP-SAT primer chapter
"How CP-SAT Reasons: The Search Core" (search_core.md) and were cross-checked
against the OR-Tools sources (``cp_model_solver_logging.cc``, ``stat_tables.cc``,
``synchronization.cc``). Keys are the stable identifiers used by the parser
(block kinds, ``table_id``s, column names, response fields) so the frontend can
look them up without knowing the OR-Tools version.

When a new table or column appears in a future OR-Tools version, add an entry
here; unknown keys simply render without explanation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

BLOCKS: dict[str, str] = {
    "solver": (
        "**Solver header.** The OR-Tools version and the parameters that differ from their "
        "defaults. Only overridden parameters are printed, so an empty list means the defaults "
        "were used. `Setting number of workers to N` appears when `num_workers` was left at 0 "
        "and CP-SAT picked the value from the available cores."
    ),
    "initial_model": (
        "**Initial model.** The model as handed to the solver: number of variables (with how many "
        "Booleans/integers appear in the objective), the variable domains, and a histogram of "
        "constraint types (`kLinear2`, `kNoOverlap`, ...). `#enforced` counts constraints with "
        "enforcement literals (reified constraints), `#terms` the total number of linear terms. "
        "Compare it with the presolved model to see how much presolve simplified."
    ),
    "presolved_model": (
        "**Presolved model.** The model that is actually searched. Presolve removes fixed and "
        "dominated variables, merges constraints and expands high-level constraints into the "
        "lower-level ones the propagators understand. A much smaller presolved model is good news; "
        "a much larger one (e.g. `kAllDiff` expanded into thousands of Booleans) explains where "
        "the search effort goes. Domains like `[0][10][20]` mean a variable with holes."
    ),
    "presolve": (
        "**Presolve log.** Each line is one presolve pass: wall time in seconds (`s`), "
        "deterministic time (`d`, a machine-independent effort measure) and the rule name in "
        "brackets, followed by counters. Lines tagged `[Symmetry]` report the automatic symmetry "
        "detection, `[SAT presolve]` the Boolean-level simplification (clause/literal counts), "
        "`[Probe]`/`[Probing]` the trial fixing of literals. Presolve runs to a fix point, so the "
        "same rules appear several times. If presolve dominates the walltime, consider "
        "`max_presolve_iterations` or a lower `cp_model_probing_level`."
    ),
    "presolve_summary": (
        "**Presolve summary.** How often each presolve rule fired and how many affine relations "
        "(`x = a*y + b`) were detected and substituted away. Rules prefixed with `TODO` are "
        "diagnostics from the developers: situations recognised but not (yet) exploited. "
        "`Problem closed by presolve.` means the search never started: presolve alone proved "
        "optimality or infeasibility."
    ),
    "search": (
        "**Search progress.** The stream of events during the parallel portfolio search. Each "
        "`#N` line is a new improving solution found by the tagged subsolver with its cost as "
        "`best:` and the still-open range as `next:[lb,ub]`; `#Bound` lines (throttled) report a "
        "worker improving the proven bound; `#Model` lines record how many variables/constraints "
        "of the presolved model are still active after sharing fixed variables; `#Done` closes the "
        "search when best meets the bound. Solutions and bounds are shared between all workers "
        "immediately, so a good incumbent from an LNS worker also speeds up the proof of the "
        "exact workers."
    ),
    "response": (
        "**Response summary.** The final status and the counters CP-SAT returns to your program. "
        "Careful: `booleans`, `conflicts`, `branches`, `propagations`, `integer_propagations` and "
        "`restarts` are **not** portfolio totals. They are copied from the single worker whose "
        "model carries the returned solution, which is often a first-solution or LNS helper that "
        "barely searched. Read the per-worker tables (Search stats) to see how hard the search "
        "really worked."
    ),
    "message": "A free-form message from the solver.",
    "comment": "Lines starting with `//` are comments added by a human, not by CP-SAT.",
    "unknown": (
        "This section was not recognised by the parser. It is kept verbatim; please report the "
        "log if you think it should be parsed."
    ),
}


class TableDoc(BaseModel):
    summary: str
    columns: dict[str, str] = Field(default_factory=dict)


TABLES: dict[str, TableDoc] = {
    "task_timing": TableDoc(
        summary=(
            "**Task timing.** How often each subsolver (task) ran and how long. The left group is "
            "wall time, the right group deterministic time (`dtime`, a hardware-independent "
            "measure of work). Full-problem workers run once for the whole search; LNS and "
            "first-solution tasks run many short rounds, so `n` is large and `avg` small. A full "
            "worker with far less `time` than the others was stopped early or started late."
        ),
        columns={
            "n": "Number of times the task ran.",
            "min": "Shortest run.",
            "max": "Longest run.",
            "avg": "Average run time.",
            "dev": "Standard deviation of the run time.",
            "time": "Total wall time / total deterministic time over all runs.",
        },
    ),
    "search_stats": TableDoc(
        summary=(
            "**Search stats.** One row per full-problem worker, straight from its SAT core. "
            "Because the portfolio runs differently configured copies of the same search loop, "
            "comparing rows shows which configuration actually searched. `Conflicts` stays at or "
            "below `Branches`; the ratio tells you whether a worker learns from nearly every "
            "decision (hard combinatorial core) or mostly descends feasibly. The two propagation "
            "columns are usually the largest by far: propagation does most of the work, branching "
            "only a little."
        ),
        columns={
            "Bools": (
                "Size of the lazily minted Boolean skeleton of this worker: Boolean variables plus "
                "the bound literals `[x <= v]` created on demand for integer variables. Each "
                "worker mints its own, so the counts differ across rows."
            ),
            "Conflicts": (
                "Number of conflicts analysed; each one produced a learned clause (nogood). "
                "A large fraction of `Branches` means the worker learns from nearly every decision."
            ),
            "Branches": (
                "Number of decisions taken over the whole search (including after restarts). "
                "No fixed relation to the variable count."
            ),
            "Restarts": (
                "How often the worker jumped back to decision level 0 while keeping learned "
                "clauses and heuristic weights. `quick_restart` configurations restart far more "
                "than steadier ones."
            ),
            "BacktrackToRoot": "Backtracks all the way to level 0 (includes restarts).",
            "Backtrack": "Total number of backtracks (undoing decisions).",
            "BoolPropag": (
                "Propagations on the Boolean trail (binary implications and clauses), read from "
                "the SAT solver's counter."
            ),
            "IntegerPropag": (
                "Bound tightenings pushed onto the integer trail. Which of the two propagation "
                "columns leads is model dependent."
            ),
        },
    ),
    "sat_formula": TableDoc(
        summary=(
            "**SAT formula.** The state of each worker's clause database at the end: how many "
            "Boolean variables got fixed or merged with an equivalent literal, how many are left, "
            "and how many binary, permanent (problem) and temporary (learned, deletable) clauses "
            "the worker holds."
        ),
        columns={
            "Fixed": "Boolean variables fixed at level 0.",
            "Equiv": "Variables replaced by an equivalent literal.",
            "Total": "Total Boolean variables of the worker.",
            "VarLeft": "Total minus fixed minus equivalent: what the search still decides on.",
            "BinaryClauses": "Clauses of size two, stored in the implication graph.",
            "PermanentClauses": "Problem clauses and learned clauses that are kept for good.",
            "TemporaryClauses": "Learned clauses that may be deleted during clause cleanup.",
        },
    ),
    "sat_stats": TableDoc(
        summary=(
            "**SAT stats.** Effort spent on keeping learned clauses short and the database small: "
            "conflict-clause minimisation, literals removed via the binary implication graph, "
            "literals learned/forgotten, and clauses subsumed during conflict analysis."
        ),
        columns={
            "ClassicMinim": "Learned clauses shortened by (recursive) clause minimisation.",
            "LitRemoved": "Literals removed from learned clauses by minimisation.",
            "LitRemovedBinary": "Literals removed using binary implications.",
            "LitLearned": "Total literals in learned clauses.",
            "LitForgotten": "Literals of learned clauses that were deleted again.",
            "Subsumed": "Clauses found redundant (subsumed) during conflict analysis.",
        },
    ),
    "vivification": TableDoc(
        summary=(
            "**Vivification.** An inprocessing technique: the solver re-asserts the literals of a "
            "clause one by one to shorten it or prove it redundant. Counters per worker."
        ),
        columns={
            "Clauses": "Clauses vivified.",
            "Decisions": "Decisions made while vivifying.",
            "LitTrue": "Clauses found already satisfied.",
            "Subsumed": "Clauses removed because a shorter one subsumes them.",
            "LitRemoved": "Literals removed from clauses.",
            "DecisionReused": "Decision prefixes reused between consecutive clauses.",
            "Conflicts": "Conflicts encountered during vivification.",
        },
    ),
    "clause_deletion": TableDoc(
        summary=(
            "**Clause deletion.** Why learned/problem clauses were removed from each worker's "
            "database (fixed at true, tautologies, promoted to binary, subsumption in various "
            "phases, blocked/eliminated by inprocessing, garbage collected). `promoted` counts "
            "clauses whose LBD improved so they became permanent; `conflicts` repeats the "
            "conflict count for reference."
        ),
    ),
    "lp_stats": TableDoc(
        summary=(
            "**Lp stats.** One row per worker that carries an LP relaxation. The LP is used as a "
            "propagator: solved with dual simplex from a warm start after each bound change, its "
            "dual values justify bound tightenings and infeasible relaxations become conflicts. "
            "Workers without a row (e.g. `no_lp`, `core`) run without linearisation."
        ),
        columns={
            "Component": "Number of independent LP components (the linear part may split).",
            "Iterations": ("Cumulative simplex pivots, kept low by dual-simplex warm starts."),
            "AddedCuts": "Cutting planes added to the relaxation (see the Lp Cut table).",
            "OPTIMAL": "LP solves that ended optimal (bound information available).",
            "DUAL_F.": (
                "Solves that stopped dual feasible (iteration limit hit; bound still valid)."
            ),
            "DUAL_U.": (
                "Dual unbounded = primal infeasible relaxation; produces a dual-ray conflict "
                "that the SAT core learns from."
            ),
        },
    ),
    "lp_dimension": TableDoc(
        summary=(
            "**Lp dimension.** Final size of the (first) LP component per worker: rows, columns "
            "and non-zeros. Larger linearisation levels give larger LPs (`max_lp`)."
        ),
    ),
    "lp_debug": TableDoc(
        summary=(
            "**Lp debug.** Internal diagnostics of the LP propagator: propagations obtained from "
            "cuts and equalities, coefficient adjustments, and numerical problems (overflow, bad "
            "cuts, bad scaling). Non-zero `Bad`/`BadScaling` hint at numerically difficult "
            "coefficients in your model."
        ),
    ),
    "lp_pool": TableDoc(
        summary=(
            "**Lp pool.** Bookkeeping of the constraint manager that decides which linear "
            "constraints and cuts are in the LP: how many are managed, how often the set was "
            "updated, and how many were simplified, merged, shortened, split or strengthened."
        ),
        columns={
            "Constraints": "Linear constraints/cuts managed for this worker.",
            "Updates": "Times the active LP constraint set was changed.",
            "Simplif": "Constraints simplified using current bounds.",
            "Merged": "Parallel constraints merged into one.",
            "Shortened": "Constraints with fixed variables removed.",
            "Split": "Constraints split into independent parts.",
            "Strengthened": (
                "Coefficient strengthening: coefficients tightened using the integrality of "
                "the variables, which makes the relaxation stronger."
            ),
            "Strenghtened": "Same as Strengthened (typo in older OR-Tools versions).",
            "Cuts/Call": "Cuts actually added / calls to the cut generators.",
        },
    ),
    "lp_cut": TableDoc(
        summary=(
            "**Lp Cut.** Cuts added per generator (rows) and worker (columns): `CG` "
            "(Chvatal-Gomory), `MIR_k` (mixed-integer rounding of k combined rows), `ZERO_HALF`, "
            "`IB` (implied bounds), `Clique`, knapsack cover, `LinMax`, and structure-specific "
            "families for scheduling/routing. Many cuts of one family indicate that this "
            "structure carries the relaxation."
        ),
    ),
    "lns_stats": TableDoc(
        summary=(
            "**LNS stats.** Large Neighbourhood Search workers fix most of the incumbent and let "
            "the full solver re-optimise a small neighbourhood. `Improv/Calls` is how often a "
            "round found a better solution versus how often it ran, `Closed` the share of rounds "
            "that solved their sub-problem completely (too high means the neighbourhoods are too "
            "easy, so the difficulty is raised), `Difficulty` the adaptive fraction of variables "
            "left free, `TimeLimit` the deterministic time budget per round."
        ),
        columns={
            "Improv/Calls": "Improving rounds / total rounds of this neighbourhood.",
            "Closed": "Percentage of rounds whose sub-problem was solved to completion.",
            "Difficulty": "Adaptive relaxation ratio (fraction of the model left free).",
            "TimeLimit": "Adaptive deterministic time limit per round.",
        },
    ),
    "ls_stats": TableDoc(
        summary=(
            "**LS stats.** Counters of the violation-based local search workers "
            "(`violation_ls`, `ls`): batches of moves, restarts/perturbations, linear and general "
            "moves, compound moves, backtracks, constraint-weight updates and score computations."
        ),
    ),
    "solutions": TableDoc(
        summary=(
            "**Solutions.** Which subsolver found how many improving solutions and how good they "
            "were: `Rank` is the range of ranks among all solutions (1 = best). Often first "
            "solutions come from feasibility jump/LNS and the last ones from exact workers or "
            "LNS. It is often more telling which subsolvers do *not* appear."
        ),
        columns={
            "Num": "Number of improving solutions reported by this subsolver.",
            "Rank": "[best rank, worst rank] of those solutions (1 = best solution).",
        },
    ),
    "objective_bounds": TableDoc(
        summary=(
            "**Objective bounds.** Which subsolver improved the proven bound how often. "
            "`initial_domain` is the trivial bound from the objective domain; bound-focused "
            "workers (`objective_lb_search`, `objective_shaving`, `lb_tree_search`, `core`) or "
            "LP-heavy workers (`max_lp`) usually dominate here."
        ),
        columns={"Num": "Number of bound improvements by this subsolver."},
    ),
    "solution_repositories": TableDoc(
        summary=(
            "**Solution repositories.** Shared pools that workers add solutions to and query "
            "from: feasible solutions (used by LNS as starting points), LP solutions and "
            "feasibility-pump solutions. `Synchro` counts synchronisation rounds."
        ),
        columns={
            "Added": "Solutions added to the pool.",
            "Queried": "Times a worker took a solution from the pool.",
            "Ignored": "Added solutions that were discarded (duplicates/worse).",
            "Synchro": "Number of synchronisations of the pool.",
        },
    ),
    "improving_bounds_shared": TableDoc(
        summary=(
            "**Improving bounds shared.** Variable bound tightenings that each worker exported "
            "to the others through the shared-bounds channel. A worker with many shared bounds "
            "contributes to everyone's propagation."
        ),
        columns={
            "Num": "Number of exported bound improvements.",
            "Sym": "Bound improvements derived from symmetry.",
        },
    ),
    "clauses_shared": TableDoc(
        summary=(
            "**Clauses shared.** Learned clauses (short, low-LBD nogoods and binary clauses) "
            "broadcast between workers. A dead end that one configuration discovers becomes a "
            "permanent constraint for all others: the portfolio learns collectively."
        ),
        columns={
            "Num": "Clauses exported by this worker.",
            "#Exported": "Clauses exported by this worker.",
            "#Imported": "Clauses imported from other workers.",
            "#BinaryRead": "Binary clauses read from the shared pool.",
            "#BinaryTotal": "Binary clauses in the shared pool.",
        },
    ),
    "linear2_shared": TableDoc(
        summary="**Linear2 shared.** Two-variable linear relations shared between workers.",
    ),
}

RESPONSE_FIELDS: dict[str, str] = {
    "status": (
        "OPTIMAL: proven optimal (or feasible for satisfaction problems). FEASIBLE: a solution "
        "was found but optimality not proven before the limit. INFEASIBLE: proven no solution. "
        "UNKNOWN: neither a solution nor a proof. MODEL_INVALID: the model is broken."
    ),
    "objective": "Objective value of the returned (best) solution.",
    "best_bound": (
        "Best proven bound on the objective. The gap between objective and bound quantifies "
        "how far the solution may be from optimal."
    ),
    "integers": "Integer variables in the returning worker's model.",
    "booleans": (
        "Boolean variables (incl. minted bound literals) of the worker that returned the solution."
    ),
    "conflicts": "Conflicts of the worker that returned the solution, not the portfolio total.",
    "branches": "Decisions of the worker that returned the solution, not the portfolio total.",
    "propagations": "Boolean propagations of the returning worker.",
    "integer_propagations": "Integer bound propagations of the returning worker.",
    "restarts": "Restarts of the returning worker.",
    "lp_iterations": "Simplex iterations of the returning worker.",
    "walltime": "Total wall-clock time of the solve.",
    "usertime": "CPU time of the main thread.",
    "deterministic_time": "Hardware-independent effort measure summed over workers.",
    "gap_integral": (
        "Integral of the relative gap over time. Smaller means the solver converged faster; "
        "useful to compare runs that end with the same status."
    ),
    "solution_fingerprint": "Hash of the returned solution.",
    "lrat_status": "Status of LRAT proof logging (NA when not enabled).",
}

SUBSOLVERS: dict[str, str] = {
    "default_lp": "Balanced default: propagation plus a light LP relaxation feeding bounds back.",
    "no_lp": "Pure CP/SAT without LP relaxation; fast and lean when the LP does not pay off.",
    "max_lp": "Heavy LP relaxation (linearization level 2) for problems with strong linear bounds.",
    "core": (
        "Core-guided optimisation: assumes objective terms at their best values and uses the "
        "unsat cores to lift the lower bound. Only scheduled for objectives with several terms."
    ),
    "quick_restart": "Restarts very aggressively; helps on problems that reward rapid re-descent.",
    "quick_restart_no_lp": "quick_restart without LP relaxation.",
    "pseudo_costs": "Branches on objective-derived estimates of variable impact (MIP style).",
    "reduced_costs": "Branches using the reduced costs of the LP relaxation.",
    "fixed": (
        "Follows the user-provided decision strategy (search_branching / add_decision_strategy)."
    ),
    "probing": "Fixes variables experimentally to derive bounds; specialises in proving.",
    "probing_max_lp": "probing with heavy LP.",
    "objective_lb_search": "Tries to disprove the current lower bound to improve it.",
    "objective_lb_search_no_lp": "objective_lb_search without LP.",
    "objective_lb_search_max_lp": "objective_lb_search with heavy LP.",
    "objective_shaving_search_no_lp": "Shaves the objective domain to prove bounds (no LP).",
    "objective_shaving_search_max_lp": "Shaves the objective domain to prove bounds (heavy LP).",
    "lb_tree_search": (
        "Explores the cheapest nodes of a search tree to improve the bound; rarely finds solutions."
    ),
    "feasibility_pump": "First-solution heuristic rounding LP solutions towards feasibility.",
    "fj": (
        "Feasibility jump: local search minimising constraint violation to find a first solution."
    ),
    "fj_restart": "Feasibility jump with restarts.",
    "violation_ls": "Violation-based local search improving/finding solutions.",
    "ls": "Local search worker.",
    "rins": "RINS/RENS LNS neighbourhood: fix variables that agree between LP and incumbent.",
    "rnd_var_lns": "LNS: free a random subset of variables.",
    "rnd_cst_lns": "LNS: free the variables of random constraints.",
    "graph_var_lns": "LNS: free a connected region of the variable graph.",
    "graph_cst_lns": "LNS: free a connected region of the constraint graph.",
    "graph_arc_lns": "LNS: free variables along arcs of the constraint graph.",
    "graph_dec_lns": "LNS: free a decomposition-based region.",
    "packing_precedences_lns": "LNS for packing: relax precedences between rectangles.",
    "packing_rectangles_lns": "LNS for packing: free a set of rectangles.",
    "packing_slice_lns": "LNS for packing: free a slice of the container.",
    "scheduling_precedences_lns": "LNS for scheduling: relax precedences.",
    "routing_path_lns": "LNS for routing: free a path segment.",
    "routing_random_lns": "LNS for routing: free random arcs.",
    "initial_domain": "Not a worker: the trivial bound from the objective's domain.",
    "neighborhood_helper": "Helper: builds LNS neighbourhoods.",
    "synchronization_agent": "Helper: synchronises shared solutions/bounds between workers.",
    "update_gap_integral": "Helper: integrates the gap over time for `gap_integral`.",
}


def describe_subsolver(name: str) -> str | None:
    if name in SUBSOLVERS:
        return SUBSOLVERS[name]
    base = name
    for suffix in ("_lns", "_default", "_random", "_lin"):
        base = base.replace(suffix, "")
    for key, text in SUBSOLVERS.items():
        if name.startswith(key) or base == key:
            return text
    if name.startswith("fs_random"):
        return "First-solution worker with randomised search (no LP variant if suffixed)."
    if name.startswith("fj_"):
        return SUBSOLVERS["fj"]
    if "lns" in name:
        return "A Large Neighbourhood Search worker."
    return None


class Explanations(BaseModel):
    blocks: dict[str, str]
    tables: dict[str, TableDoc]
    response_fields: dict[str, str]
    subsolvers: dict[str, str]


def all_explanations() -> Explanations:
    return Explanations(
        blocks=BLOCKS, tables=TABLES, response_fields=RESPONSE_FIELDS, subsolvers=SUBSOLVERS
    )

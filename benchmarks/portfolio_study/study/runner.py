"""Run CP-SAT on a benchmark instance with a controlled portfolio and store the log.

Created 2026-09-27 for the portfolio-importance study. A ``RunConfig`` names the
instance, worker count, time limit, seed and the portfolio restriction (whitelist via
``subsolvers`` or blacklist via ``ignore_subsolvers``). Runs are stored under
``portfolio_study/runs/<problem>/<instance>/<key>.txt`` (+ ``.json``) and skipped when
present, so every experiment script is resumable.

How the worker budget is split (CP-SAT 9.15, cp_model_search.cc):
    full subsolvers F(n) = 1 (n=1), n-1 (n<=4), n-2 (n<=8), n-(n//4+1) (n<=16)
    the remaining threads run first-solution workers and then the interleaved LNS/LS.
Passing exactly F(n) names in ``subsolvers`` keeps the split identical to the default
(fewer names would be padded by repeating the first one).

Usage::

    from portfolio_study.study.runner import RunConfig, run_jobs
    jobs = [RunConfig("jobshop", "swv06", workers=8, time_limit=10, seed=s) for s in (0, 1)]
    run_jobs(jobs, budget=12)        # runs in parallel while sum(workers) <= budget
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]  # benchmarks/
RUNS = ROOT / "portfolio_study" / "runs"
DATA = ROOT / "data"

ABBREV = {
    "default_lp": "dlp", "fixed": "fix", "core": "core", "no_lp": "nolp", "max_lp": "mlp",
    "max_lp_sym": "mlps", "quick_restart": "qr", "reduced_costs": "rc",
    "quick_restart_no_lp": "qrnl", "pseudo_costs": "pc", "lb_tree_search": "lbt",
    "probing": "prb", "objective_lb_search": "olb", "objective_shaving_no_lp": "osnl",
    "objective_shaving_max_lp": "osml", "probing_max_lp": "prbml", "probing_no_lp": "prbnl",
    "objective_lb_search_no_lp": "olbnl", "objective_lb_search_max_lp": "olbml",
}
# Interleaved (LNS/LS) names, for Phase G file names; "rins/rens" must not become a directory.
POOL_ABBREV = {
    "rins/rens": "rins", "feasibility_pump": "fp", "ls": "ls", "graph_arc_lns": "garc",
    "graph_cst_lns": "gcst", "graph_dec_lns": "gdec", "graph_var_lns": "gvar",
    "rnd_cst_lns": "rcst", "rnd_var_lns": "rvar", "scheduling_intervals_lns": "sint",
    "scheduling_precedences_lns": "sprec", "scheduling_resource_windows_lns": "srw",
    "scheduling_time_window_lns": "stw", "routing_path_lns": "rpath",
    "routing_full_path_lns": "rfull", "routing_random_lns": "rrnd",
    "packing_random_lns": "prnd", "packing_square_lns": "psq", "packing_swap_lns": "pswap",
    "packing_precedences_lns": "pprec", "packing_rectangles_lns": "prect",
}


def _abbrev(name: str) -> str:
    return ABBREV.get(name) or POOL_ABBREV.get(name) or name.replace("/", "-")


def default_full_count(num_workers: int) -> int:
    """Number of full-problem subsolvers CP-SAT schedules by default (no shared tree)."""
    n = num_workers
    if n <= 1:
        return 1
    if n <= 4:
        return n - 1
    if n <= 8:
        return n - 2
    if n <= 16:
        return n - (n // 4 + 1)
    return n - (n // 2 - 3)


@dataclass(frozen=True)
class RunConfig:
    problem: str
    instance: str
    workers: int
    time_limit: float
    seed: int = 0
    subsolvers: tuple[str, ...] = ()  # exact whitelist; empty = CP-SAT default order
    ignore: tuple[str, ...] = ()  # blacklist (globs), applied on top
    num_full: int | None = None  # override num_full_subsolvers
    params: dict[str, Any] = field(default_factory=dict)  # any extra CP-SAT parameters

    @property
    def setname(self) -> str:
        parts = []
        if self.subsolvers:
            parts.append("sub-" + "+".join(_abbrev(s) for s in self.subsolvers))
        if self.ignore:
            parts.append("ign-" + "+".join(sorted(_abbrev(s) for s in self.ignore)))
        if self.num_full is not None:
            parts.append(f"nf{self.num_full}")
        for k, v in sorted(self.params.items()):
            parts.append(f"{k}={v}")
        return "_".join(parts) if parts else "default"

    @property
    def key(self) -> str:
        return f"w{self.workers}_t{int(self.time_limit)}_{self.setname}_s{self.seed}"

    @property
    def log_path(self) -> Path:
        return RUNS / self.problem / self.instance / (self.key + ".txt")

    @property
    def meta_path(self) -> Path:
        return self.log_path.with_suffix(".json")

    def exists(self) -> bool:
        return self.meta_path.exists()


def _solve(cfg: RunConfig) -> dict[str, Any]:
    """Build and solve in the current process; returns the metadata dict."""
    sys.path.insert(0, str(ROOT))
    from ortools.sat.python import cp_model

    from bench.problems import all_problems

    problem = all_problems()[cfg.problem]
    data_dir = DATA / cfg.problem
    inst = next(i for i in problem.instances(data_dir) if i.name == cfg.instance)
    model = problem.build(inst)
    solver = cp_model.CpSolver()
    p = solver.parameters
    p.max_time_in_seconds = cfg.time_limit
    p.num_workers = cfg.workers
    p.random_seed = cfg.seed
    p.log_search_progress = True
    p.log_to_stdout = False
    p.log_subsolver_statistics = True
    if cfg.subsolvers:
        p.subsolvers.extend(cfg.subsolvers)
    if cfg.ignore:
        p.ignore_subsolvers.extend(cfg.ignore)
    if cfg.num_full is not None:
        p.num_full_subsolvers = cfg.num_full
    for k, v in cfg.params.items():
        setattr(p, k, v)
    lines: list[str] = []
    solver.log_callback = lines.append
    t0 = time.time()
    status = solver.solve(model)
    has_obj = model.proto.has_objective() if hasattr(model.proto, "has_objective") else model.proto.HasField("objective")
    meta = {
        "config": asdict(cfg),
        "key": cfg.key,
        "status": solver.status_name(status),
        "objective": solver.objective_value if has_obj else None,
        "best_bound": solver.best_objective_bound if has_obj else None,
        "wall_time": solver.wall_time,
        "elapsed": round(time.time() - t0, 2),
        "started_at": t0,
    }
    cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cfg.meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return meta


def run_jobs(jobs: list[RunConfig], budget: int = 12, verbose: bool = True) -> int:
    """Run all missing jobs, packing them so that the running worker count stays <= budget.

    Returns the number of runs executed. Jobs are started largest-first so an 8-worker run
    is not starved by a queue of 2-worker runs.
    """
    pending = sorted((j for j in jobs if not j.exists()), key=lambda j: -j.workers)
    skipped = len(jobs) - len(pending)
    if verbose:
        print(f"[runner] {len(pending)} to run, {skipped} cached, budget={budget} workers")
    done = 0
    t_start = time.time()
    with ProcessPoolExecutor(max_workers=max(1, budget)) as pool:
        running: dict = {}
        used = 0
        while pending or running:
            started = False
            for j in list(pending):
                if used + j.workers <= budget or not running:
                    running[pool.submit(_solve, j)] = j
                    used += j.workers
                    pending.remove(j)
                    started = True
                    if used >= budget:
                        break
            if not running:
                continue
            if started and pending and used < budget:
                continue
            finished, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for f in finished:
                j = running.pop(f)
                used -= j.workers
                done += 1
                try:
                    m = f.result()
                    if verbose:
                        print(f"[{done}/{len(pending) + done + len(running)}] {j.problem}/{j.instance} {j.key}: "
                              f"{m['status']} obj={m['objective']} lb={m['best_bound']} ({time.time() - t_start:.0f}s)", flush=True)
                except Exception as exc:  # noqa: BLE001 - keep the batch going
                    print(f"FAILED {j.problem}/{j.instance} {j.key}: {exc!r}", file=sys.stderr, flush=True)
    return done


def load_meta(cfg: RunConfig) -> dict[str, Any]:
    return json.loads(cfg.meta_path.read_text())

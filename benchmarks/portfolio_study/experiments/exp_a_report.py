"""Phase A report: per instance the primal activity in the 8-worker/10 s runs and the
per-subsolver signals. Decides which instances stay in the study.
    uv run python -m portfolio_study.experiments.exp_a_report
"""

from cpsat_logutils import parse_log

from portfolio_study.study.candidates import PHASE_A
from portfolio_study.study.evaluate import trajectory
from portfolio_study.study.runner import RunConfig
from portfolio_study.study.signals import extract_signals, full_subsolver_names


def main() -> None:
    for p, i in PHASE_A:
        objs = []
        for seed in (0, 1):
            cfg = RunConfig(p, i, workers=8, time_limit=10, seed=seed)
            if not cfg.exists():
                continue
            log = parse_log(cfg.log_path.read_text())
            if log.search is None or log.response is None or log.response.status is None:
                continue
            traj = trajectory(log)
            full = set(full_subsolver_names(log))
            sols = [e for e in log.search.events if e.solution_index is not None]
            late = [e for e in sols if e.time > 3.0]
            by_full = sum(1 for e in sols if e.subsolver in full)
            late_full = sum(1 for e in late if e.subsolver in full)
            objs.append(traj[-1][1] if traj else None)
            print(f"{p}/{i} s{seed}: {log.response.status.value} obj={traj[-1][1] if traj else None} "
                  f"nsol={len(sols)} (full {by_full}) after3s={len(late)} (full {late_full}) "
                  f"first={traj[0][0] if traj else None}s last={traj[-1][0] if traj else None}s")
            sig = extract_signals(log, 10.0)
            for s in sorted(sig.values(), key=lambda s: -s.improvement_share):
                print(f"    {s.name:14s} sol={s.n_solutions:3d} imp={s.n_improvements:3d} share={s.improvement_share:.2f} "
                      f"late={s.late_share:.2f} rank={s.first_rank}-{s.last_rank} first={int(s.found_first)} lb={s.n_bounds:4d} "
                      f"shared={s.shared_bounds:6d} confl={s.conflicts:8d} done={int(s.done)}")
        a, b = (objs + [None, None])[:2]
        if a is not None and b is not None:
            print(f"  noise between seeds: {abs(a - b) / max(abs(a), 1):.3%}")


if __name__ == "__main__":
    main()

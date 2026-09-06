"""CLI of the benchmark harness.

    uv run python run.py list
    uv run python run.py download jobshop
    uv run python run.py solve jobshop --limit 60 --workers 8 --max-instances 5
    uv run python run.py solve --all --limit 60 --workers 8 --max-instances 3

Logs go to logs/<problem>/, instance data to data/<problem>/ (both git-ignored).
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from bench.problems import all_problems
from bench.runner import solve_and_log

ROOT = Path(__file__).resolve().parent
DATA, LOGS = ROOT / "data", ROOT / "logs"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("download")
    d.add_argument("problems", nargs="*")
    s = sub.add_parser("solve")
    s.add_argument("problems", nargs="*")
    s.add_argument("--all", action="store_true", help="explicit form of the default (all problems)")
    s.add_argument("--limit", type=float, default=60.0)
    s.add_argument("--workers", type=int, default=8)
    s.add_argument("--max-instances", type=int, default=0, help="0 = all; else spread over sizes")
    s.add_argument("--instance", action="append", default=[], help="only these instance names")
    s.add_argument("--force", action="store_true")
    s.add_argument("--param", action="append", default=[], help="extra CP-SAT parameter key=value")
    s.add_argument("--tag", default="", help="suffix for the log file name (use with --param)")
    args = ap.parse_args()

    problems = all_problems()
    if args.cmd == "list":
        for name, p in sorted(problems.items()):
            print(f"{name:24s} {p.description}")
        return 0
    names = args.problems or sorted(problems)  # no names given = every problem
    unknown = [n for n in names if n not in problems]
    if unknown:
        print("unknown problems:", ", ".join(unknown), file=sys.stderr)
        return 2
    for name in names:
        problem = problems[name]
        data_dir = DATA / name
        data_dir.mkdir(parents=True, exist_ok=True)
        problem.download(data_dir)
        if args.cmd == "download":
            print(f"{name}: {len(problem.instances(data_dir))} instances")
            continue
        instances = problem.instances(data_dir)
        if args.instance:
            instances = [i for i in instances if i.name in args.instance]
        if args.max_instances:
            instances = _spread(instances, args.max_instances)
        extra = dict(_parse_param(p) for p in args.param)
        for inst in instances:
            try:
                meta = solve_and_log(
                    problem, inst, LOGS, time_limit=args.limit, workers=args.workers,
                    extra_params=extra, tag=args.tag, force=args.force
                )
            except Exception:  # noqa: BLE001 - keep the batch going
                print(f"{name}/{inst.name}: FAILED", file=sys.stderr)
                traceback.print_exc()
                continue
            if meta is None:
                print(f"{name}/{inst.name}: skipped (log exists)")
            else:
                print(f"{name}/{inst.name}: {meta['status']} obj={meta['objective']} bound={meta['best_bound']} {meta['wall_time']:.1f}s")
    return 0


def _spread(instances: list, count: int) -> list:
    """Pick ``count`` instances spread over the (file-size sorted) list.

    Taking the first N would only ever cover the smallest instances of a set;
    spreading keeps a mix of trivial and hard instances in the corpus.
    """
    if count >= len(instances):
        return instances

    def size(inst) -> int:
        return inst.path.stat().st_size if inst.path and inst.path.exists() else 0

    ordered = sorted(instances, key=lambda i: (size(i), i.name))
    step = (len(ordered) - 1) / max(count - 1, 1)
    picked = sorted({round(k * step) for k in range(count)})
    return [ordered[i] for i in picked]


def _parse_param(text: str) -> tuple[str, object]:
    key, _, value = text.partition("=")
    for conv in (int, float):
        try:
            return key, conv(value)
        except ValueError:
            pass
    if value.lower() in {"true", "false"}:
        return key, value.lower() == "true"
    return key, value


if __name__ == "__main__":
    sys.exit(main())

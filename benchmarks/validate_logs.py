"""Parse every collected log with the ``cpsat_logutils`` parser and report gaps.

Created 2026-09-06: the point of the benchmark corpus is to find log shapes the
parser or the analyzer does not handle yet, so this script parses `logs/**/*.txt`
and prints, per problem, how many logs parsed, which raised, and which sections
ended up in ``log.unparsed``. Run it after a batch (``uv run python validate_logs.py``).
"""

from __future__ import annotations

import collections
import sys
import traceback
from pathlib import Path

from cpsat_logutils import parse_log

LOGS = Path(__file__).resolve().parent / "logs"


def main() -> int:
    files = sorted(LOGS.rglob("*.txt"))
    if not files:
        print("no logs found", file=sys.stderr)
        return 2
    failures: list[tuple[Path, str]] = []
    unparsed: collections.Counter[str] = collections.Counter()
    missing: collections.Counter[str] = collections.Counter()
    per_problem: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for path in files:
        problem = str(path.parent.relative_to(LOGS))
        per_problem[problem][1] += 1
        try:
            log = parse_log(path.read_text())
        except Exception:  # noqa: BLE001 - report every parser failure, keep going
            failures.append((path, traceback.format_exc(limit=3)))
            continue
        per_problem[problem][0] += 1
        for chunk in log.unparsed:
            first = chunk.lines[0].value if chunk.lines else "<empty>"
            unparsed[first.strip()[:80]] += 1
        for field in ("solver", "initial_model", "presolve_summary", "search", "response"):
            if getattr(log, field, None) is None:
                missing[f"{problem}:{field}"] += 1
    print(f"parsed {sum(v[0] for v in per_problem.values())}/{len(files)} logs\n")
    for problem, (ok, total) in sorted(per_problem.items()):
        flag = "" if ok == total else "  <-- failures"
        print(f"  {problem:34s} {ok:4d}/{total:<4d}{flag}")
    if missing:
        print("\nmissing top-level sections:")
        for key, count in missing.most_common(20):
            print(f"  {count:4d}x {key}")
    if unparsed:
        print("\nunparsed chunks (first line, most common):")
        for line, count in unparsed.most_common(30):
            print(f"  {count:4d}x {line}")
    for path, tb in failures[:5]:
        print(f"\n=== {path} ===\n{tb}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

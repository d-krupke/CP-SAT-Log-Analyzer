"""Mine the collected logs for things the analyzer's knowledge base misses.

Created 2026-09-06 alongside `validate_logs.py`. Where that script asks "does the
parser understand the log", this one asks "does the knowledge base explain it":
it collects every subsolver/worker name, every statistics table and every table
column that occurs in `logs/**/*.txt` and prints the ones that have no entry in
`knowledge/*.toml`. Run it after a batch; the output is a to-do list for the
knowledge base.

    uv run python mine_patterns.py
"""

from __future__ import annotations

import collections
import fnmatch
import re
import sys
import tomllib
from pathlib import Path

from cpsat_logutils import parse_log

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
KNOWLEDGE = ROOT.parent / "knowledge"


def _knowledge(name: str) -> dict:
    path = KNOWLEDGE / f"{name}.toml"
    return tomllib.loads(path.read_text()) if path.exists() else {}


def _documents_subsolver(name: str, keys: set[str], patterns: list[str]) -> bool:
    """Mirror of ``app.explanations.describe_subsolver``: exact key, prefix, then glob."""
    if name in keys:
        return True
    if any(name.startswith(k + "_") for k in keys):
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def main() -> int:
    subsolver_doc = _knowledge("subsolvers")
    subsolvers = subsolver_doc.get("subsolvers", {})
    patterns = [p["pattern"] for p in subsolver_doc.get("patterns", [])]
    constraints = _knowledge("constraints").get("constraints", {})
    tables = _knowledge("tables")
    known_tables = set(tables.get("tables", {})) | set(tables.get("columns", {}))

    workers: collections.Counter[str] = collections.Counter()
    kinds: collections.Counter[str] = collections.Counter()
    table_names: collections.Counter[str] = collections.Counter()
    statuses: collections.Counter[str] = collections.Counter()
    messages: collections.Counter[str] = collections.Counter()
    files = sorted(LOGS.rglob("*.txt"))
    for path in files:
        try:
            log = parse_log(path.read_text())
        except Exception:  # noqa: BLE001,S112 - validate_logs.py is what reports failures
            continue
        if log.search:
            for ev in log.search.events:
                if ev.subsolver:
                    workers[ev.subsolver] += 1
        for model in (log.initial_model, log.presolved_model):
            for line in getattr(model, "constraints", []) or []:
                kinds[line.name] += 1
        for name in _tables_of(log):
            table_names[name] += 1
        if log.response and log.response.status:
            statuses[log.response.status.value] += 1
        for block in log.messages:
            first = block.lines[0].value if block.lines else ""
            generic = re.sub(r"\d+(\.\d+)?", "N", first)[:60]
            messages[f"{block.message_kind}: {generic}"] += 1

    print(f"mined {len(files)} logs\n")
    keys = set(subsolvers)
    _report("subsolvers seen", workers, {n for n in workers if _documents_subsolver(n, keys, patterns)})
    _report("constraint kinds seen", kinds, set(constraints))
    _report("statistics tables seen", table_names, known_tables)
    print("\nstatuses:", ", ".join(f"{k}={v}" for k, v in statuses.most_common()))
    print("\nmost common messages (kind: text with numbers masked):")
    for text, count in messages.most_common(15):
        print(f"  {count:5d}x {text}")
    return 0


def _tables_of(log) -> list[str]:
    names = []
    for field, value in log.stats:
        if value is None or isinstance(value, (list, str)):
            continue  # `raw`/`other` hold leftovers, not a single named table
        names.append(getattr(value, "name", None) or field)
    return names


def _report(title: str, seen: collections.Counter[str], known: set[str]) -> None:
    missing = [name for name in seen if name not in known]
    print(f"{title}: {len(seen)} distinct, {len(missing)} undocumented")
    for name in sorted(seen, key=lambda n: -seen[n]):
        mark = "  " if name in known else "??"
        print(f"  {mark} {seen[name]:6d}x {name}")


if __name__ == "__main__":
    sys.exit(main())

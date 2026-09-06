"""Collect CP-SAT logs from the MiniZinc Challenge benchmark suite.

Created 2026-09-06 as part of the local benchmark corpus (see README.md). The
other problem classes build CP-SAT models directly in Python; this script instead
drives the bundled MiniZinc 2.10 compiler with the OR-Tools ``cp-sat`` backend, so
the logs show what models produced by a modelling language look like (huge numbers
of Booleans, `mznfile...` model names, FlatZinc-style search strategies).

MiniZinc prints the CP-SAT log as FlatZinc comments (``%% `` prefix); the prefix is
stripped so the stored file is a plain CP-SAT log the analyzer can read.

Usage (families are directories of `data/minizinc/repo`):

    uv run python mzn_run.py list
    uv run python mzn_run.py solve --limit 60 --workers 8 --max-instances 2
    uv run python mzn_run.py solve rcpsp steelmillslab --limit 30

Change it when the MiniZinc bundle moves (``tools/``) or when the instance
selection should cover more/other families.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "data" / "minizinc" / "repo"
LOGS = ROOT / "logs" / "minizinc"
BUNDLE = ROOT / "tools" / "MiniZincIDE-2.10.1-x86_64-linux-gnu" / "bin" / "minizinc"
FLATTEN_GRACE = 300.0  # seconds granted on top of the solve limit for flattening
MEMORY_LIMIT_MB = 8000  # CP-SAT aborts itself instead of being OOM-killed
_RESPONSE_FIELD = re.compile(r"^[a-z_]+: ")


@dataclass(frozen=True)
class MznInstance:
    """One runnable pair: a model and (optionally) a data file."""

    family: str
    name: str
    model: Path
    data: Path | None

    @property
    def size(self) -> int:
        return (self.data or self.model).stat().st_size


def families() -> list[str]:
    return sorted(p.name for p in REPO.iterdir() if p.is_dir() and not p.name.startswith("."))


def _models(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.mzn") if not p.name.endswith("_alt.mzn"))


def _model_for(data: Path, family_dir: Path) -> Path | None:
    """The model belonging to a data file: nearest ancestor directory with a model.

    Families store data either next to the model or in subdirectories
    (``talent_scheduling/easy/*.dzn``), so walk upwards. A model whose stem is a
    prefix of the data file's stem wins (``2DPacking.mzn`` vs ``2DLevelPacking.mzn``).
    """
    directory = data.parent
    while True:
        models = _models(directory)
        if models:
            for m in models:
                if data.stem.startswith(m.stem):
                    return m
            return models[0]
        if directory == family_dir:
            return None
        directory = directory.parent


def discover(family: str) -> list[MznInstance]:
    family_dir = REPO / family
    data_files = sorted(p for p in family_dir.rglob("*.dzn") if p.is_file())
    instances = []
    for data in data_files:
        model = _model_for(data, family_dir)
        if model is None:
            continue
        rel = data.relative_to(family_dir).with_suffix("")
        instances.append(
            MznInstance(family, str(rel).replace("/", "_"), model, data)
        )
    return instances or standalone(family)


def standalone(family: str) -> list[MznInstance]:
    """The family's models as instances of their own (no data file).

    Some families ship self-contained models (``talent_scheduling_01.mzn``); in
    ``zephyrus`` the data files do not even fit the model that sits next to them, so
    this is also the fallback when every pairing of a family fails.
    """
    family_dir = REPO / family
    return [MznInstance(family, m.stem, m, None) for m in sorted(family_dir.rglob("*.mzn"))]


def spread(instances: list[MznInstance], count: int) -> list[MznInstance]:
    """Pick ``count`` instances evenly spread over the size-sorted list.

    Taking the first N would only ever solve the smallest instances of a family;
    spreading over the sizes gives a mix of trivial and hard logs.
    """
    ordered = sorted(instances, key=lambda i: (i.size, i.name))
    if count <= 0 or count >= len(ordered):
        return ordered
    step = (len(ordered) - 1) / max(count - 1, 1)
    picked = {round(k * step) for k in range(count)}
    return [ordered[i] for i in sorted(picked)]


def _params(time_limit: float, workers: int) -> str:
    return ",".join(
        [
            f"max_time_in_seconds:{time_limit}",
            f"num_workers:{workers}",
            "log_search_progress:true",
            "log_subsolver_statistics:true",
            f"max_memory_in_mb:{MEMORY_LIMIT_MB}",
        ]
    )


def _split_output(text: str) -> tuple[str, list[str]]:
    """Separate the CP-SAT log (``%% `` comments) from MiniZinc's own output."""
    log: list[str] = []
    other: list[str] = []
    for line in text.splitlines():
        if line.startswith("%%%mzn"):  # MiniZinc statistics, not part of the CP-SAT log
            other.append(line)
        elif line.startswith("%%"):
            log.append(line[3:] if line.startswith("%% ") else line[2:])
        elif line.strip():
            other.append(line)
    log, trailing = _cut_model_output(log)
    return "\n".join(log) + "\n", other + trailing


def _cut_model_output(lines: list[str]) -> tuple[list[str], list[str]]:
    """Drop what the model's own `output` statement printed through the same channel.

    The flatzinc interpreter prefixes those lines with ``%% `` as well, so they would end
    up inside the stored log after the response summary (``Mario earned 628 gold coins``,
    ``TIMEOUT``). The response summary is the last thing CP-SAT itself prints, so keep
    everything up to its final ``field: value`` line.
    """
    summary = [i for i, line in enumerate(lines) if line.startswith("CpSolverResponse summary:")]
    if not summary:
        return lines, []
    end = summary[-1] + 1
    for i in range(summary[-1] + 1, len(lines)):
        if _RESPONSE_FIELD.match(lines[i]):
            end = i + 1
    return lines[:end], lines[end:]


def run(inst: MznInstance, *, time_limit: float, workers: int, force: bool) -> dict | None:
    out_dir = LOGS / inst.family
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{inst.name}__w{workers}_t{int(time_limit)}"
    log_path, meta_path = out_dir / f"{stem}.txt", out_dir / f"{stem}.json"
    if log_path.exists() and not force:
        return None
    cmd = [
        str(BUNDLE), "--solver", "cp-sat", "-s",
        "--params", _params(time_limit, workers), str(inst.model),
    ]
    if inst.data is not None:
        cmd.append(str(inst.data))
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=time_limit + FLATTEN_GRACE, check=False
    )
    log, other = _split_output(proc.stdout)
    if "Starting CP-SAT solver" not in log:
        raise RuntimeError(f"no CP-SAT log ({proc.returncode}): {proc.stderr.strip()[:300]}")
    log_path.write_text(log)
    meta = {
        "problem": f"minizinc/{inst.family}",
        "instance": inst.name,
        "model": str(inst.model.relative_to(REPO)),
        "data": str(inst.data.relative_to(REPO)) if inst.data else None,
        "time_limit": time_limit,
        "workers": workers,
        "returncode": proc.returncode,
        "log_lines": log.count("\n"),
        "minizinc_output": other[-40:],
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("solve")
    s.add_argument("families", nargs="*")
    s.add_argument("--limit", type=float, default=60.0)
    s.add_argument("--workers", type=int, default=8)
    s.add_argument("--max-instances", type=int, default=2, help="0 = all (a lot!)")
    s.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if not REPO.is_dir():
        print(f"missing {REPO}; clone MiniZinc/minizinc-benchmarks there", file=sys.stderr)
        return 2
    names = args.families if args.cmd == "solve" and args.families else families()
    unknown = [n for n in names if not (REPO / n).is_dir()]
    if unknown:
        print("unknown families:", ", ".join(unknown), file=sys.stderr)
        return 2
    if args.cmd == "list":
        for family in names:
            found = discover(family)
            print(f"{family:22s} {len(found):5d} instances")
        return 0
    for family in names:
        picked = spread(discover(family), args.max_instances)
        if _solve_all(picked, args) == 0 and picked and picked[0].data is not None:
            print(f"{family}: no run succeeded, retrying with the models alone", file=sys.stderr)
            _solve_all(spread(standalone(family), args.max_instances), args)
    return 0


def _solve_all(instances: list[MznInstance], args: argparse.Namespace) -> int:
    """Run each instance; returns how many produced (or already had) a log."""
    done = 0
    for inst in instances:
        try:
            meta = run(inst, time_limit=args.limit, workers=args.workers, force=args.force)
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            print(f"{inst.family}/{inst.name}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        done += 1
        if meta is None:
            print(f"{inst.family}/{inst.name}: skipped (log exists)")
        else:
            tail = meta["minizinc_output"][-1] if meta["minizinc_output"] else ""
            print(f"{inst.family}/{inst.name}: {meta['log_lines']} log lines | {tail[:60]}")
    return done


if __name__ == "__main__":
    sys.exit(main())

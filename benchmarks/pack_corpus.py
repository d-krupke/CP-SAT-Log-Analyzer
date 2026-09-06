"""Pack the locally collected benchmark logs into the committed regression corpus.

Created 2026-09-06: ``benchmarks/logs/`` is git-ignored (16 MB, and the instances
behind it may be copyrighted), but the logs themselves are plain CP-SAT output and
are the best regression input the project has. This script writes
``v2/corpus/benchmark_logs.tar.xz`` (~1 MB) so the parser and the analyzer can be
tested against every collected log; see ``v2/corpus/README.md``.

Run it after collecting a new batch, then commit the archive::

    uv run python benchmarks/pack_corpus.py

Deliberately *not* copied into the archive: the per-run JSON sidecars. The MiniZinc
ones embed the solver's full solution output (assignments of a third-party model), so
instead of the sidecars we store a normalized ``index.json`` with only the metadata
the tests need - problem, instance, parameters, version, status, objective, bound,
walltime, model sizes and the source URL (not the sidecars' `log_lines`, which counts
only the lines CP-SAT sent to the callback and disagrees with the stored file). Change that mapping in ``_entry`` if a test
needs another field, and keep it free of instance or solution data.

The tar members get fixed owner/mtime/order, so re-packing an unchanged corpus
produces a byte-identical archive (no churn in git).
"""

from __future__ import annotations

import io
import json
import lzma
import tarfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
OUT = HERE.parent / "v2" / "corpus" / "benchmark_logs.tar.xz"
MTIME = 1767225600  # 2026-01-01 00:00:00 UTC, fixed for reproducible archives

# Sidecar fields copied verbatim into the index (missing ones are simply left out).
_NATIVE_FIELDS = (
    "problem",
    "instance",
    "source",
    "parameters",
    "ortools_version",
    "status",
    "objective",
    "best_bound",
    "wall_time",
    "num_variables",
    "num_constraints",
)


def _entry(meta: dict[str, Any]) -> dict[str, Any]:
    """Normalize one sidecar to the metadata the tests are allowed to see."""
    if "minizinc_output" in meta:  # driven through MiniZinc: different shape
        entry: dict[str, Any] = {
            "problem": meta.get("problem", ""),
            "instance": meta.get("instance", ""),
            "origin": "minizinc",
            "model": meta.get("model", ""),  # file name only, never its content
            "data": meta.get("data", ""),
            "parameters": {
                "max_time_in_seconds": meta.get("time_limit"),
                "num_workers": meta.get("workers"),
            },
        }
        return entry
    entry = {key: meta[key] for key in _NATIVE_FIELDS if meta.get(key) is not None}
    entry["origin"] = "native"
    return entry


def build_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(LOGS.rglob("*.txt")):
        sidecar = path.with_suffix(".json")
        meta = json.loads(sidecar.read_text()) if sidecar.is_file() else {}
        index[str(path.relative_to(LOGS))] = _entry(meta)
    return index


def _add(tar: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mtime = MTIME
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tar.addfile(info, io.BytesIO(payload))


def main() -> int:
    if not LOGS.is_dir():
        print(f"no logs at {LOGS} - run the collector first")
        return 2
    index = build_index()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        _add(tar, "index.json", json.dumps(index, indent=1, sort_keys=True).encode())
        for name in index:
            _add(tar, f"logs/{name}", (LOGS / name).read_bytes())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(lzma.compress(raw.getvalue(), preset=9 | lzma.PRESET_EXTREME))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(index)} logs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

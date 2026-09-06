"""Access to the committed benchmark log corpus (``v2/corpus/benchmark_logs.tar.xz``).

Created 2026-09-06 so the parser can be tested against all 295 collected CP-SAT logs
instead of the handful of example logs. The archive is read once per session; see
``v2/corpus/README.md`` for its layout and how to regenerate it. The backend tests keep
their own copy of this helper - it is a dozen lines and neither project imports the
other's tests.
"""

from __future__ import annotations

import json
import tarfile
from functools import lru_cache
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parents[2] / "corpus" / "benchmark_logs.tar.xz"


@lru_cache(maxsize=1)
def load_corpus() -> tuple[dict[str, str], dict[str, dict]]:
    """Return ``({log name: text}, {log name: metadata})`` from the archive."""
    logs: dict[str, str] = {}
    with tarfile.open(ARCHIVE, "r:xz") as tar:
        index_member = tar.extractfile("index.json")
        assert index_member is not None
        index = json.load(index_member)
        for name in index:
            member = tar.extractfile(f"logs/{name}")
            assert member is not None, name
            logs[name] = member.read().decode()
    return logs, index


def corpus_names() -> list[str]:
    """Log names for parametrisation; empty when the archive is not checked out."""
    if not ARCHIVE.is_file():
        return []
    return sorted(load_corpus()[0])

"""Shared helpers for the cpsatlog tests: locate the repository's example logs.

``example_logs/`` holds the logs the frontend offers on its landing page;
``example_logs/archive/`` holds the ones that were retired from that list (older
OR-Tools versions, redundant parameter variants). The parser must still handle both,
so the fixtures below cover the archive as well - it is the only coverage of the
9.3 ... 9.10 log formats.
"""

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "example_logs"
ARCHIVE_DIR = EXAMPLE_DIR / "archive"


def example_paths() -> list[Path]:
    """Every example log, the archived ones included."""
    return sorted(EXAMPLE_DIR.glob("*.txt")) + sorted(ARCHIVE_DIR.glob("*.txt"))


def read_example(name: str) -> str:
    path = EXAMPLE_DIR / name
    if not path.is_file():
        path = ARCHIVE_DIR / name
    return path.read_text()


@pytest.fixture(params=example_paths(), ids=lambda p: p.name)
def example_log(request: pytest.FixtureRequest) -> tuple[str, str]:
    path: Path = request.param
    return path.name, path.read_text()

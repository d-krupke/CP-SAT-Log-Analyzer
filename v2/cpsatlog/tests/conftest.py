"""Shared helpers for the cpsatlog tests: locate the repository's example logs."""

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parents[3] / "example_logs"


def example_paths() -> list[Path]:
    return sorted(EXAMPLE_DIR.glob("*.txt"))


def read_example(name: str) -> str:
    return (EXAMPLE_DIR / name).read_text()


@pytest.fixture(params=example_paths(), ids=lambda p: p.name)
def example_log(request: pytest.FixtureRequest) -> tuple[str, str]:
    path: Path = request.param
    return path.name, path.read_text()

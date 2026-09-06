"""Serve the bundled example logs (``example_logs/`` at the repository root).

The directory is resolved from ``EXAMPLE_LOGS_DIR`` (set in Docker) or, for
local development, from the repository layout ``backend/app`` -> ``../../../example_logs``.
Curated descriptions come from ``knowledge/examples.toml``.

Only the top level is served: ``example_logs/archive/`` holds logs that were retired from
the landing page (older OR-Tools versions, redundant parameter variants) but are still
parsed by the test suites, so the glob here stays non-recursive on purpose.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from cpsat_logutils import parse_log
from pydantic import BaseModel, Field

from .knowledge import load


class ExampleInfo(BaseModel):
    name: str
    version_hint: str
    description: str = Field(description="Curated text about the origin of the log (may be empty)")
    summary: str = Field(description="Derived from the log: problem type, size, status, time")


def examples_dir() -> Path:
    env = os.environ.get("EXAMPLE_LOGS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "example_logs"


def _version_hint(name: str) -> str:
    prefix = name.split("_", 1)[0]
    if prefix.isdigit() and len(prefix) >= 2:
        return f"9.{prefix[1:]}"
    return "?"


def list_examples() -> list[ExampleInfo]:
    directory = examples_dir()
    if not directory.is_dir():
        return []
    result = []
    for path in sorted(directory.glob("*.txt")):  # non-recursive: skips archive/
        name = path.stem
        result.append(
            ExampleInfo(
                name=name,
                version_hint=_version_hint(name),
                description=load("examples")["examples"].get(name, ""),
                summary=_auto_description(path),
            )
        )
    return result


@lru_cache(maxsize=64)
def _auto_description(path: Path) -> str:
    """One-line summary derived from the log itself for examples without a curated text."""
    try:
        log = parse_log(path.read_text(errors="replace"))
    except Exception:  # noqa: BLE001 - a broken example must not break the listing
        return ""
    parts: list[str] = []
    if log.initial_model:
        if log.initial_model.problem_type:
            parts.append(log.initial_model.problem_type.capitalize() + " problem")
        if log.initial_model.num_variables:
            parts.append(f"{log.initial_model.num_variables.value:,} variables")
    if log.response and log.response.status:
        status = log.response.status.value
        wall = log.response.walltime.value if log.response.walltime else None
        parts.append(f"{status}" + (f" after {wall:.1f} s" if wall is not None else ""))
    return ", ".join(parts) + "." if parts else ""


def read_example(name: str) -> str | None:
    if not name.replace("_", "").isalnum():
        return None
    path = examples_dir() / f"{name}.txt"
    if not path.is_file():
        return None
    return path.read_text(errors="replace")

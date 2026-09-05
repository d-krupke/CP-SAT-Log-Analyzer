"""Serve the bundled example logs (``example_logs/`` at the repository root).

The directory is resolved from ``EXAMPLE_LOGS_DIR`` (set in Docker) or, for
local development, from the repository layout ``v2/backend/app`` -> ``../../../example_logs``.
Descriptions come from the old Streamlit app so users know where a log stems from.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

DESCRIPTIONS: dict[str, str] = {
    "98_02": "TSP with MTZ constraints, not solved to optimality within the time limit.",
    "98_03": "TSP with AddCircuit constraint, easily solved to optimality.",
    "98_04": "Multi-Knapsack: solved to optimality after a longer search.",
    "98_05": "Packing problem: not solved within the time limit.",
    "98_06": "Packing problem: solved to optimality after a short search.",
    "98_07": "Knapsack problem, mostly solved by presolve (old MacBook).",
    "98_08": "One iteration of the SampLNS algorithm.",
    "97_01": "Small teaching example.",
    "93_01": "Log of an old OR-Tools version (9.3) with the legacy log format.",
    "915_01": (
        "OR-Tools 9.15: knapsack with integer quantities and an AllDifferent side constraint."
    ),
}


class ExampleInfo(BaseModel):
    name: str
    version_hint: str
    description: str


def examples_dir() -> Path:
    env = os.environ.get("EXAMPLE_LOGS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "example_logs"


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
    for path in sorted(directory.glob("*.txt")):
        name = path.stem
        result.append(
            ExampleInfo(
                name=name,
                version_hint=_version_hint(name),
                description=DESCRIPTIONS.get(name, "Example log."),
            )
        )
    return result


def read_example(name: str) -> str | None:
    if not name.replace("_", "").isalnum():
        return None
    path = examples_dir() / f"{name}.txt"
    if not path.is_file():
        return None
    return path.read_text(errors="replace")

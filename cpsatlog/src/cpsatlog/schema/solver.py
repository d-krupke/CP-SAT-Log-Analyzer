"""Schema for the log header: solver version, parameters and worker count."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Block, Loc


class SolverInfo(Block):
    kind: str = "solver"
    version: Loc[str] | None = Field(default=None, description="e.g. '9.15.6755'")
    version_tuple: tuple[int, int, int] | None = None
    parameters: Loc[dict[str, Any]] | None = Field(
        default=None, description="Parameters overridden by the user, parsed from the proto text"
    )
    parameters_raw: str | None = None
    num_workers: Loc[int] | None = Field(
        default=None,
        description="From 'Setting number of workers to N' (printed when num_workers was 0)",
    )
    num_shared_tree_workers: Loc[int] | None = Field(
        default=None,
        description=(
            "From 'Setting number of shared tree workers to N', printed when "
            "shared_tree_num_workers was left at -1 and the automatic rule enabled it"
        ),
    )
    other_lines: list[Loc[str]] = Field(default_factory=list)

"""Schema for the solution-hint lines CP-SAT prints.

Created 2026-09: the hint is the one place where the caller's own input shows up
in the log, and "was my hint accepted, and did the solver use it?" is a question
the analyzer must be able to answer. ``CpSatLog.hints`` collects every
hint-related line with its classification and the numbers it carries; the
interpretation (was a hint given at all, what became of it) is derived from that
in the backend.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HintNoteKind = Literal[
    "hint_complete_feasible",
    "hint_complete_infeasible",
    "hint_incomplete",
    "hint_outside_domain",
    "hint_breaks_assumptions",
    "hint_fixed_variables",
    "hint_ignored",
    "hint_debug_only",
    "hint_other",
]


class HintNote(BaseModel):
    """One hint-related log line, classified.

    ``numbers`` holds what the wording carried: ``hinted``/``active`` for an
    incomplete hint, ``objective`` for a feasible one, ``variables`` for the
    presolve line that fixes hinted variables.
    """

    line: int = Field(ge=1)
    kind: HintNoteKind
    text: str
    numbers: dict[str, float] = Field(default_factory=dict)

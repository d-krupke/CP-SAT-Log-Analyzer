"""Recognize the solution-hint lines, wherever in the log they appear.

Created 2026-09 together with ``schema.hints``. CP-SAT checks the hint twice --
once on the model as given and once on the presolved model
(``SolutionHintIsCompleteAndFeasible`` in ``cp_model_solver.cc``) -- and the
resulting line is *not* a block of its own: when presolve closes the model the
message sits between ``Preloading model.`` and ``#Model``, i.e. inside the
presolve block. Like the progress events, these lines are therefore collected by
scanning every line of the log (see ``assemble.parse_log``).

When to change: add a pattern when a new OR-Tools version rewords a line, and
keep the old ones so old logs keep parsing. The kinds are mirrored in
``knowledge/messages.toml``.
"""

from __future__ import annotations

import re

from ..schema.hints import HintNote, HintNoteKind
from ..text import NUMBER_TOKEN, parse_float

# Specific wordings first; the trailing catch-all keeps unknown variants visible.
_PATTERNS: list[tuple[re.Pattern[str], HintNoteKind]] = [
    (
        re.compile(
            # 9.8 and older said "... out of N variables hinted."
            r"^The solution hint is incomplete: (?P<hinted>\d+) out of (?P<active>\d+)"
            r" (?:non fixed )?variables hinted\."
        ),
        "hint_incomplete",
    ),
    (
        re.compile(r"^The solution hint is complete but it contains values outside"),
        "hint_outside_domain",
    ),
    (
        re.compile(r"^The solution hint is complete and feasible, but it breaks the assumptions"),
        "hint_breaks_assumptions",
    ),
    (
        re.compile(
            r"^The solution hint is complete and is feasible\."
            rf"(?: Its objective value is (?P<objective>{NUMBER_TOKEN})\.)?"
        ),
        "hint_complete_feasible",
    ),
    (
        re.compile(r"^The solution hint is complete, but it is infeasible"),
        "hint_complete_infeasible",
    ),
    (
        re.compile(r"^Fixing (?P<variables>\d+) variables to their value in the solution hints\."),
        "hint_fixed_variables",
    ),
    (re.compile(r"^Ignoring solution hint"), "hint_ignored"),
    (re.compile(r"^Using solution hint only as debug solution"), "hint_debug_only"),
    (re.compile(r"^The solution hint"), "hint_other"),
]


def parse_hint_note(line: str, line_no: int) -> HintNote | None:
    """Classify ``line`` as a hint-related message, or return ``None``."""
    text = line.strip()
    for pattern, kind in _PATTERNS:
        match = pattern.match(text)
        if match is None:
            continue
        numbers = {}
        for name, raw in match.groupdict().items():
            value = parse_float(raw) if raw is not None else None
            if value is not None:
                numbers[name] = value
        return HintNote(line=line_no, kind=kind, text=text, numbers=numbers)
    return None

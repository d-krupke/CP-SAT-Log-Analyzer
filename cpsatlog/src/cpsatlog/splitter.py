"""Split raw log text into blank-line separated chunks with line numbers.

CP-SAT separates its sections with blank lines, but not reliably: ``Problem
closed by presolve.`` may be glued to the response summary, ``LRAT_status``
precedes ``CpSolverResponse summary:`` without a blank line, and user code often
prints extra text. This module only cuts the text into ``Chunk`` objects; it
never interprets them. Add new forced cut points to ``_CUT_BEFORE`` /
``_CUT_AFTER`` when a future OR-Tools version glues sections together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_CUT_BEFORE = re.compile(
    r"^(?:CpSolverResponse summary:|LRAT_status:|Starting (?:search|Search|deterministic search|"
    r"sequential search|presolve|CP-SAT solver)|Presolve summary:|Task timing|"
    r"(?:Initial|Presolved) \w+ model )"
)
_CUT_AFTER = re.compile(r"^Problem closed by presolve\.$")
_COMMENT = re.compile(r"^//")


@dataclass
class Chunk:
    """Consecutive non-blank lines. ``start``/``end`` are 1-based inclusive."""

    start: int
    lines: list[str] = field(default_factory=list)

    @property
    def end(self) -> int:
        return self.start + len(self.lines) - 1

    @property
    def first(self) -> str:
        return self.lines[0] if self.lines else ""

    def numbered(self) -> list[tuple[int, str]]:
        return [(self.start + i, line) for i, line in enumerate(self.lines)]


def split_lines(text: str) -> list[str]:
    """Normalize line endings and trailing whitespace; keeps 1:1 line count."""
    return [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def split_into_chunks(lines: list[str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_start = 0

    def close() -> None:
        if buffer:
            chunks.append(Chunk(start=buffer_start, lines=list(buffer)))
            buffer.clear()

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            close()
            continue
        is_comment = bool(_COMMENT.match(line))
        if buffer:
            was_comment = bool(_COMMENT.match(buffer[-1]))
            glued_to_lrat = line.startswith("CpSolverResponse") and buffer[-1].startswith(
                "LRAT_status:"
            )
            if is_comment != was_comment or (_CUT_BEFORE.match(line) and not glued_to_lrat):
                close()
        if not buffer:
            buffer_start = idx
        buffer.append(line)
        if _CUT_AFTER.match(line):
            close()
    close()
    return chunks

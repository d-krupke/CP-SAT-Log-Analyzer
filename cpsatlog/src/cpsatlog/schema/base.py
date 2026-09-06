"""Base building blocks of the line-anchored schema.

Every piece of parsed data must be traceable to the log line(s) it came from so
that a UI can map between raw text and parsed content. Three primitives cover
all cases:

* ``LineSpan`` – an inclusive 1-based range of lines (a whole block).
* ``Loc[T]`` – a scalar value together with the single line it was read from.
* ``Block`` – base class for every top-level log section (carries ``kind`` and
  ``span``).

Extending: derive new section models from ``Block`` and wrap scalar fields in
``Loc[...]`` when they come from one specific line.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LineSpan(BaseModel):
    """Inclusive, 1-based range of log lines."""

    start: int = Field(ge=1)
    end: int = Field(ge=1)

    def contains(self, line: int) -> bool:
        return self.start <= line <= self.end

    @property
    def num_lines(self) -> int:
        return self.end - self.start + 1


class Loc[T](BaseModel):
    """A parsed value plus the line it was taken from."""

    model_config = ConfigDict(frozen=True)

    value: T
    line: int = Field(ge=1)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Loc({self.value!r} @ {self.line})"


class Block(BaseModel):
    """Common base for every parsed log section."""

    kind: str
    span: LineSpan


class RawBlock(Block):
    """A blank-line separated block that no parser claimed (kept verbatim)."""

    kind: str = "unknown"
    lines: list[Loc[str]] = Field(default_factory=list)


class CommentBlock(Block):
    """Lines starting with ``//`` – not produced by CP-SAT but often added by humans."""

    kind: str = "comment"
    lines: list[Loc[str]] = Field(default_factory=list)


class MessageBlock(Block):
    """Free-form solver messages such as ``Problem closed by presolve.``."""

    kind: str = "message"
    message_kind: str = "generic"
    lines: list[Loc[str]] = Field(default_factory=list)

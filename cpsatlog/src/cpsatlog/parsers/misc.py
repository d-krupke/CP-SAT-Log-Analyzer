"""Parsers for comments, known one-line messages and the raw fallback."""

from __future__ import annotations

import re

from ..schema.base import CommentBlock, LineSpan, MessageBlock, RawBlock
from ..splitter import Chunk
from .base import BlockParser, locs
from .hints import parse_hint_note

_MESSAGES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^Problem closed by presolve\."), "closed_by_presolve"),
    (re.compile(r"^(Relative|Absolute) gap limit of .* reached\."), "gap_limit_reached"),
    (re.compile(r"^Starting to load the model"), "loading_model"),
    (re.compile(r"^INFEASIBLE:"), "infeasible"),
    (re.compile(r"^Unsat after presolving"), "infeasible"),
    (re.compile(r"^Sub-solver search statistics:"), "legacy_subsolver_stats"),
    (
        re.compile(r"^Setting number of tasks in each batch of interleaved search"),
        "interleave_batch_size",
    ),
]


def _message_kind(line: str) -> str | None:
    """The kind of a known one-line message, or ``None`` for anything else.

    Hint lines are classified by ``parsers.hints`` so that a standalone hint chunk and a hint
    line buried in the presolve block get the same kind.
    """
    note = parse_hint_note(line, 1)
    if note is not None:
        return note.kind
    for pattern, kind in _MESSAGES:
        if pattern.match(line):
            return kind
    return None


class CommentParser(BlockParser):
    kind = "comment"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return chunk.first.startswith("//")

    @classmethod
    def parse(cls, chunk: Chunk) -> CommentBlock:
        return CommentBlock(span=LineSpan(start=chunk.start, end=chunk.end), lines=locs(chunk))


class MessageParser(BlockParser):
    kind = "message"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return _message_kind(chunk.first) is not None

    @classmethod
    def parse(cls, chunk: Chunk) -> MessageBlock:
        return MessageBlock(
            span=LineSpan(start=chunk.start, end=chunk.end),
            message_kind=_message_kind(chunk.first) or "generic",
            lines=locs(chunk),
        )


class RawParser(BlockParser):
    kind = "unknown"

    @classmethod
    def matches(cls, chunk: Chunk) -> bool:
        return True

    @classmethod
    def parse(cls, chunk: Chunk) -> RawBlock:
        return RawBlock(span=LineSpan(start=chunk.start, end=chunk.end), lines=locs(chunk))

"""Parsers for comments, known one-line messages and the raw fallback."""

from __future__ import annotations

import re

from ..schema.base import CommentBlock, LineSpan, MessageBlock, RawBlock
from ..splitter import Chunk
from .base import BlockParser, locs

_MESSAGES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^Problem closed by presolve\."), "closed_by_presolve"),
    (re.compile(r"^(Relative|Absolute) gap limit of .* reached\."), "gap_limit_reached"),
    (re.compile(r"^Starting to load the model"), "loading_model"),
    (re.compile(r"^The solution hint"), "hint"),
    (re.compile(r"^INFEASIBLE:"), "infeasible"),
    (re.compile(r"^Unsat after presolving"), "infeasible"),
    (re.compile(r"^Sub-solver search statistics:"), "legacy_subsolver_stats"),
    (
        re.compile(r"^Setting number of tasks in each batch of interleaved search"),
        "interleave_batch_size",
    ),
]


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
        return any(p.match(chunk.first) for p, _ in _MESSAGES)

    @classmethod
    def parse(cls, chunk: Chunk) -> MessageBlock:
        message_kind = next(k for p, k in _MESSAGES if p.match(chunk.first))
        return MessageBlock(
            span=LineSpan(start=chunk.start, end=chunk.end),
            message_kind=message_kind,
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

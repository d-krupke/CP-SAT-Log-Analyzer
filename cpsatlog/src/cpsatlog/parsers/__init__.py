"""Ordered registry of block parsers. First match wins."""

from __future__ import annotations

from ..schema.base import Block
from ..splitter import Chunk
from .base import BlockParser
from .header import SolverParser
from .misc import CommentParser, MessageParser, RawParser
from .model import ModelParser
from .presolve import PresolveParser, PresolveSummaryParser
from .response import ResponseParser
from .search import SearchParser
from .tables import KeyValueListParser, TableParser, TaskTimingParser

REGISTRY: list[type[BlockParser]] = [
    CommentParser,
    SolverParser,
    ModelParser,
    PresolveSummaryParser,
    PresolveParser,
    ResponseParser,
    SearchParser,
    TaskTimingParser,
    TableParser,
    KeyValueListParser,
    MessageParser,
    RawParser,
]


def parse_chunk(chunk: Chunk) -> Block:
    for parser in REGISTRY:
        if parser.matches(chunk):
            return parser.parse(chunk)
    return RawParser.parse(chunk)  # pragma: no cover - RawParser always matches


__all__ = ["REGISTRY", "BlockParser", "parse_chunk"]

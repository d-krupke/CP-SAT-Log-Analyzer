"""Parser plug-in interface and registry.

Each section of the log is handled by one ``BlockParser`` subclass that decides
via ``matches`` whether it understands a chunk and turns it into a schema
``Block`` via ``parse``. Parsers are tried in ``REGISTRY`` order; the first
match wins, so put specific parsers before generic ones. To support a new log
section: write a parser, add it to ``REGISTRY`` in ``parsers/__init__.py`` and
give the assembler a home for the new block.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema.base import Block, Loc
from ..splitter import Chunk


class BlockParser(ABC):
    kind: str = "unknown"

    @classmethod
    @abstractmethod
    def matches(cls, chunk: Chunk) -> bool: ...

    @classmethod
    @abstractmethod
    def parse(cls, chunk: Chunk) -> Block: ...


def locs(chunk: Chunk) -> list[Loc[str]]:
    return [Loc(value=line, line=no) for no, line in chunk.numbered()]

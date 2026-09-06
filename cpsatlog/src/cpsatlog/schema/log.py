"""Root model ``CpSatLog`` – the JSON-serializable result of ``parse_log``.

Access pattern::

    log = parse_log(text)
    log.response.status.value          # "OPTIMAL"
    log.response.status.line           # 157
    log.search.events[0].objective
    log.stats.search_stats.row("core").values["Conflicts"]
    log.block_at(line=42)              # which section does line 42 belong to?

Every section is ``None`` when the log does not contain it. ``blocks`` is an
ordered index of all recognized sections with their line spans and a JSON
pointer into this model, which is what a UI uses to map clicks in the raw text
to parsed data and back.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import CommentBlock, LineSpan, MessageBlock, RawBlock
from .hints import HintNote
from .model import ModelDescription
from .presolve import PresolveLog, PresolveSummary
from .response import ResponseSummary
from .search import SearchProgress
from .solver import SolverInfo
from .tables import FinalStats


class BlockRef(BaseModel):
    kind: str
    span: LineSpan
    path: str = Field(description="JSON pointer to the parsed data, e.g. '/stats/search_stats'")
    title: str = ""


class CpSatLog(BaseModel):
    num_lines: int
    solver: SolverInfo | None = None
    initial_model: ModelDescription | None = None
    presolve: PresolveLog | None = None
    presolve_summary: PresolveSummary | None = None
    presolved_model: ModelDescription | None = None
    search: SearchProgress | None = None
    stats: FinalStats = Field(default_factory=FinalStats)
    response: ResponseSummary | None = None
    messages: list[MessageBlock] = Field(default_factory=list)
    hints: list[HintNote] = Field(
        default_factory=list, description="Hint-related lines, collected from the whole log"
    )
    comments: list[CommentBlock] = Field(default_factory=list)
    unparsed: list[RawBlock] = Field(default_factory=list)
    blocks: list[BlockRef] = Field(default_factory=list, description="Ordered index of sections")
    warnings: list[str] = Field(default_factory=list)

    def block_at(self, line: int) -> BlockRef | None:
        for ref in self.blocks:
            if ref.span.contains(line):
                return ref
        return None

    @property
    def version(self) -> tuple[int, int, int] | None:
        return self.solver.version_tuple if self.solver else None

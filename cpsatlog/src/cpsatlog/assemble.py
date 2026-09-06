"""Turn parsed chunks into one ``CpSatLog``.

Responsibilities that go beyond single chunks live here: merging the several
chunks that make up the presolve or the search phase, collecting stray progress
lines (``#Bound ... initial_domain`` inside presolve) and the hint lines,
deriving the objective sense, placing tables into ``FinalStats`` and building the
ordered block index that maps lines back to parsed data.
"""

from __future__ import annotations

from .parsers import parse_chunk
from .parsers.events import parse_event
from .parsers.hints import parse_hint_note
from .schema.base import Block, CommentBlock, LineSpan, Loc, MessageBlock, RawBlock
from .schema.log import BlockRef, CpSatLog
from .schema.model import ModelDescription
from .schema.presolve import PresolveLog, PresolveSummary
from .schema.response import ResponseSummary
from .schema.search import ObjectiveSense, SearchEvent, SearchProgress
from .schema.solver import SolverInfo
from .schema.tables import FinalStats, Table, TaskTimingTable
from .splitter import Chunk, split_into_chunks, split_lines


def parse_log(text: str) -> CpSatLog:
    lines = split_lines(text)
    chunks = split_into_chunks(lines)
    log = CpSatLog(num_lines=len(lines))
    stray_events: list[SearchEvent] = []
    for chunk in chunks:
        block = parse_chunk(chunk)
        path = _place(log, block, chunk)
        if log.blocks and log.blocks[-1].path == path:
            log.blocks[-1].span = LineSpan(start=log.blocks[-1].span.start, end=block.span.end)
        else:
            log.blocks.append(
                BlockRef(kind=block.kind, span=block.span, path=path, title=_title(block))
            )
        if not isinstance(block, SearchProgress):
            stray_events.extend(
                e for e in (parse_event(line, no) for no, line in chunk.numbered()) if e
            )
    _finish_search(log, stray_events)
    # Hint lines are not a block of their own: when presolve closes the model the
    # message sits inside the presolve block, so scan the whole log for them.
    log.hints = [
        note for note in (parse_hint_note(line, no) for no, line in enumerate(lines, 1)) if note
    ]
    return log


def _title(block: Block) -> str:
    if isinstance(block, Table | TaskTimingTable):
        return block.title
    if isinstance(block, ModelDescription):
        return f"{block.stage.title()} model"
    if isinstance(block, MessageBlock):
        return block.message_kind
    return block.kind.replace("_", " ")


def _place(log: CpSatLog, block: Block, chunk: Chunk) -> str:
    """Store ``block`` in ``log`` and return the JSON pointer to it."""
    match block:
        case SolverInfo():
            if log.solver is None:
                log.solver = block
                return "/solver"
            log.warnings.append(f"Second solver header at line {block.span.start}; kept the first.")
            return _unparsed(log, block, chunk)
        case ModelDescription():
            attr = "initial_model" if block.stage == "initial" else "presolved_model"
            if getattr(log, attr) is None:
                setattr(log, attr, block)
                return f"/{attr}"
            log.warnings.append(
                f"Second {block.stage} model at line {block.span.start}; kept the first."
            )
            return _unparsed(log, block, chunk)
        case PresolveLog():
            if log.presolve is None:
                log.presolve = block
            else:
                _merge_presolve(log.presolve, block)
            return "/presolve"
        case PresolveSummary():
            if log.presolve_summary is None:
                log.presolve_summary = block
                return "/presolve_summary"
            existing = log.presolve_summary
            if block.closed_by_presolve and not existing.closed_by_presolve:
                existing.closed_by_presolve = block.closed_by_presolve
                existing.span = LineSpan(start=existing.span.start, end=block.span.end)
                return "/presolve_summary"
            log.warnings.append(
                f"Second presolve summary at line {block.span.start}; kept the first."
            )
            return _unparsed(log, block, chunk)
        case SearchProgress():
            if log.search is None:
                log.search = block
            else:
                _merge_search(log.search, block)
            return "/search"
        case TaskTimingTable():
            if log.stats.task_timing is None:
                log.stats.task_timing = block
                return "/stats/task_timing"
            log.stats.other.append(_as_generic(block))
            return f"/stats/other/{len(log.stats.other) - 1}"
        case Table():
            if (
                block.table_id in FinalStats.model_fields
                and getattr(log.stats, block.table_id) is None
            ):
                setattr(log.stats, block.table_id, block)
                return f"/stats/{block.table_id}"
            log.stats.other.append(block)
            return f"/stats/other/{len(log.stats.other) - 1}"
        case ResponseSummary():
            if log.response is None:
                log.response = block
                return "/response"
            log.warnings.append(
                f"Second response summary at line {block.span.start}; kept the first."
            )
            return _unparsed(log, block, chunk)
        case MessageBlock():
            if block.message_kind == "closed_by_presolve" and log.presolve_summary is not None:
                summary = log.presolve_summary
                summary.closed_by_presolve = Loc(value=True, line=block.lines[0].line)
            log.messages.append(block)
            return f"/messages/{len(log.messages) - 1}"
        case CommentBlock():
            log.comments.append(block)
            return f"/comments/{len(log.comments) - 1}"
        case RawBlock():
            if (
                log.messages
                and log.blocks
                and log.blocks[-1].path == f"/messages/{len(log.messages) - 1}"
            ):
                last = log.messages[-1]
                if last.message_kind == "legacy_subsolver_stats":
                    last.lines.extend(block.lines)
                    last.span = LineSpan(start=last.span.start, end=block.span.end)
                    return log.blocks[-1].path
            return _unparsed(log, block, chunk)
        case _:
            return _unparsed(log, block, chunk)


def _unparsed(log: CpSatLog, block: Block, chunk: Chunk) -> str:
    """Keep ``block`` verbatim under ``/unparsed`` so the UI can show what was not used.

    A block that a parser produced but that cannot be stored (a second solver header, a
    duplicated response) is turned back into raw lines: dropping the text would leave the
    reader with a warning and nothing to look at.
    """
    if isinstance(block, RawBlock):
        raw = block
    else:
        raw = RawBlock(
            kind=block.kind,
            span=block.span,
            lines=[
                Loc(value=line, line=no) for no, line in chunk.numbered() if block.span.contains(no)
            ],
        )
    log.unparsed.append(raw)
    return f"/unparsed/{len(log.unparsed) - 1}"


def _as_generic(table: TaskTimingTable) -> Table:
    return Table(
        span=table.span, table_id=table.table_id, title=table.title, header_line=table.header_line
    )


def _merge_presolve(target: PresolveLog, extra: PresolveLog) -> None:
    target.spans.append(extra.span)
    target.span = LineSpan(
        start=min(target.span.start, extra.span.start), end=max(target.span.end, extra.span.end)
    )
    if target.start_time is None:
        target.start_time = extra.start_time
    target.steps.extend(extra.steps)
    target.symmetry_lines.extend(extra.symmetry_lines)
    target.sat_presolve_lines.extend(extra.sat_presolve_lines)
    target.messages.extend(extra.messages)


def _merge_search(target: SearchProgress, extra: SearchProgress) -> None:
    target.spans.append(extra.span)
    target.span = LineSpan(
        start=min(target.span.start, extra.span.start), end=max(target.span.end, extra.span.end)
    )
    if target.start is None:
        target.start = extra.start
    target.subsolvers.extend(extra.subsolvers)
    target.events.extend(extra.events)


def _finish_search(log: CpSatLog, stray_events: list[SearchEvent]) -> None:
    if log.search is None and not stray_events:
        return
    if log.search is None:
        first = min(stray_events, key=lambda e: e.line)
        span = LineSpan(start=first.line, end=first.line)
        log.search = SearchProgress(span=span, spans=[])
    log.search.events.extend(stray_events)
    log.search.events.sort(key=lambda e: e.line)
    log.search.objective_sense = _objective_sense(log.search.events)


def _objective_sense(events: list[SearchEvent]) -> ObjectiveSense | None:
    """``best`` sits at the ``ub`` side for minimization and at the ``lb`` side for maximization."""
    for e in events:
        if e.objective_infinite == "inf":
            return "minimize"
        if e.objective_infinite == "-inf":
            return "maximize"
        if e.objective is None or e.next_lb is None or e.next_ub is None:
            continue
        if e.objective > e.next_ub:
            return "minimize"
        if e.objective < e.next_lb:
            return "maximize"
    return None

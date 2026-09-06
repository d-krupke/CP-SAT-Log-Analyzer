"""The parser must survive broken, incomplete and foreign input without losing its anchoring.

Created 2026-09-06. A log analyzer is pointed at logs that went wrong, so the interesting
inputs are exactly the damaged ones: a run that was killed mid-search, a log clipped by a
terminal, one prefixed by a logging framework, a stack trace pasted by mistake. None of that
may raise, and the line anchoring (every non-blank line belongs to exactly one block) must
hold, because the UI maps clicks in the raw text through that index.

The variants are built by ``damage.py``; what the analysis makes of them is tested in the
backend suite (``test_broken.py`` there).
"""

from __future__ import annotations

import pytest

from cpsatlog import CpSatLog, parse_log
from cpsatlog.splitter import split_lines

from .conftest import read_example
from .damage import NOT_A_LOG, damaged_variants, drop_head, duplicate, truncate

HEALTHY = read_example("915_jobshop_8workers.txt")
VARIANTS = damaged_variants(HEALTHY)


@pytest.fixture(params=list(VARIANTS), ids=list(VARIANTS))
def damaged(request: pytest.FixtureRequest) -> tuple[str, str]:
    return request.param, VARIANTS[request.param]


def test_parsing_never_raises(damaged: tuple[str, str]) -> None:
    name, text = damaged
    log = parse_log(text)
    assert log.num_lines == len(split_lines(text)), name


def test_block_index_stays_sorted_disjoint_and_complete(damaged: tuple[str, str]) -> None:
    """Same invariant as for healthy logs: the UI relies on it for every input."""
    name, text = damaged
    log = parse_log(text)
    lines = split_lines(text)
    prev_end = 0
    for ref in log.blocks:
        assert 1 <= ref.span.start <= ref.span.end <= log.num_lines, (name, ref)
        assert ref.span.start > prev_end, (name, ref)
        prev_end = ref.span.end
    for no, line in enumerate(lines, start=1):
        # Blank lines may fall inside a merged block (presolve, search); text may not be lost.
        assert log.block_at(no) is not None or not line.strip(), (name, no, line)


def test_unparsed_blocks_are_reachable_and_keep_their_text(damaged: tuple[str, str]) -> None:
    """Unrecognized text must be shown, so it needs both an index entry and its lines."""
    name, text = damaged
    log = parse_log(text)
    lines = split_lines(text)
    paths = {ref.path for ref in log.blocks}
    for i, block in enumerate(log.unparsed):
        assert f"/unparsed/{i}" in paths, (name, i)
        assert block.lines, (name, i, block.span)
        assert [loc.line for loc in block.lines] == list(
            range(block.span.start, block.span.end + 1)
        ), (name, i)
        for loc in block.lines:
            assert loc.value == lines[loc.line - 1], (name, loc.line)


def test_json_round_trip(damaged: tuple[str, str]) -> None:
    name, text = damaged
    log = parse_log(text)
    assert CpSatLog.model_validate_json(log.model_dump_json()) == log, name


def test_empty_input_yields_an_empty_log() -> None:
    """No sections, no unparsed text, no crash - the caller decides what to tell the user."""
    for text in ("", "   \n\n\t\n"):
        log = parse_log(text)
        assert log.blocks == [] and log.unparsed == []
        assert log.solver is None and log.response is None and log.search is None


def test_foreign_text_is_kept_verbatim_as_unparsed() -> None:
    """A pasted stack trace or prose must end up visible, not silently dropped."""
    log = parse_log(NOT_A_LOG)
    assert log.solver is None
    assert len(log.unparsed) == 1
    assert [loc.value for loc in log.unparsed[0].lines] == NOT_A_LOG.strip().split("\n")


def test_truncated_log_keeps_what_came_before_the_cut() -> None:
    """A killed run has no response summary; everything up to the cut must still be parsed."""
    log = parse_log(truncate(HEALTHY, 0.5))
    assert log.response is None
    assert log.solver is not None and log.initial_model is not None
    assert log.search is not None and log.search.events


def test_log_without_its_head_still_parses_the_rest() -> None:
    """Users often paste only the tail of a log."""
    log = parse_log(drop_head(HEALTHY, 40))
    assert log.solver is None
    assert log.response is not None and log.response.status is not None
    assert log.search is not None and log.search.events


def test_two_runs_in_one_file_are_reported_and_kept() -> None:
    """The second run's sections cannot be merged, so they are warned about and kept verbatim."""
    log = parse_log(duplicate(HEALTHY))
    assert any("solver header" in w for w in log.warnings)
    assert any("response summary" in w for w in log.warnings)
    assert log.unparsed, "the duplicate sections must remain visible"
    assert all(block.lines for block in log.unparsed)

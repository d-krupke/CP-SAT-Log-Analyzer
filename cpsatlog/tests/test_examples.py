"""Every example log (OR-Tools 9.3 ... 9.15) must parse into a consistent CpSatLog.

These tests check invariants rather than exact values: no exceptions, a
response block, a well-formed non-overlapping block index that covers every
non-blank line, and a lossless JSON round trip. Exact values for selected logs
live in ``test_specific.py``.
"""

from __future__ import annotations

from cpsatlog import CpSatLog, parse_log


def test_parses_and_has_response(example_log: tuple[str, str]) -> None:
    name, text = example_log
    log = parse_log(text)
    assert log.response is not None, name
    assert log.response.status is not None, name
    assert log.solver is not None and log.solver.version_tuple is not None, name
    assert log.initial_model is not None, name


def test_block_index_is_sorted_disjoint_and_covers_all_lines(example_log: tuple[str, str]) -> None:
    name, text = example_log
    log = parse_log(text)
    lines = text.splitlines()
    assert log.num_lines >= len(lines)
    prev_end = 0
    covered: set[int] = set()
    for ref in log.blocks:
        assert ref.span.start > prev_end, (name, ref)
        prev_end = ref.span.end
        covered.update(range(ref.span.start, ref.span.end + 1))
    for no, line in enumerate(lines, start=1):
        if line.strip():
            assert no in covered, (name, no, line)
        assert log.block_at(no) is not None or not line.strip()


def test_json_round_trip(example_log: tuple[str, str]) -> None:
    name, text = example_log
    log = parse_log(text)
    dumped = log.model_dump_json()
    restored = CpSatLog.model_validate_json(dumped)
    assert restored == log, name


def test_no_unknown_blocks_in_modern_logs(example_log: tuple[str, str]) -> None:
    """Logs from 9.7 upwards contain only known sections; 9.3 has a legacy stats dump."""
    name, text = example_log
    log = parse_log(text)
    if log.version and log.version >= (9, 7, 0):
        assert log.unparsed == [], (name, [b.span for b in log.unparsed])


def test_search_events_are_sorted_and_anchored(example_log: tuple[str, str]) -> None:
    name, text = example_log
    log = parse_log(text)
    if log.search is None:
        return
    lines = text.splitlines()
    last = 0
    for event in log.search.events:
        assert event.line > last, name
        last = event.line
        assert lines[event.line - 1].startswith(event.label) or event.label == "", (name, event)


def test_tables_anchor_rows_to_lines(example_log: tuple[str, str]) -> None:
    name, text = example_log
    log = parse_log(text)
    lines = text.splitlines()
    for table in log.stats.all_tables():
        assert lines[table.header_line - 1].startswith(table.title.split(" (")[0]), (
            name,
            table.title,
        )
        for row in table.rows:
            assert row.name in lines[row.line - 1], (name, table.title, row.name)

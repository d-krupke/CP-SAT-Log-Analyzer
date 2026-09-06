"""The parser must handle every log of the committed benchmark corpus (295 real logs).

Created 2026-09-06: the example logs cover old OR-Tools versions but only a few solve
shapes. The corpus adds 21 problem classes and 30 MiniZinc families with worker counts
1/8/16 and parameter variants (`interleave_search`, `use_lns_only`, `cp_model_presolve`,
`linearization_level`, `enumerate_all_solutions`), which is what actually caught the
parser gaps so far.

What is asserted per log: it parses, nothing lands in ``log.unparsed``, the mandatory
sections exist, and the parsed response agrees with ``index.json`` - the metadata the
solver library itself reported for that run, so this cross-checks the parser against
OR-Tools rather than against itself. Add a value here only if the index carries it; see
``corpus/README.md``.

Skipped entirely when the archive is not present.
"""

from __future__ import annotations

import pytest

from cpsatlog import CpSatLog, parse_log

from .corpus import ARCHIVE, corpus_names, load_corpus

pytestmark = pytest.mark.skipif(not ARCHIVE.is_file(), reason=f"no corpus at {ARCHIVE}")

NAMES = corpus_names()


def test_archive_holds_the_whole_corpus() -> None:
    """A truncated or half-regenerated archive should fail loudly, not silently shrink."""
    logs, index = load_corpus()
    assert len(logs) == len(index) == 295
    assert sorted(logs) == sorted(index)
    assert {meta["origin"] for meta in index.values()} == {"native", "minizinc"}


@pytest.mark.parametrize("name", NAMES)
def test_log_parses_completely(name: str) -> None:
    """Every corpus log parses, and every non-blank line ends up in a known section."""
    logs, _ = load_corpus()
    log = parse_log(logs[name])
    assert log.unparsed == [], [chunk.lines[0].value for chunk in log.unparsed]
    assert log.solver is not None
    assert log.initial_model is not None
    assert log.response is not None and log.response.status is not None


@pytest.mark.parametrize("name", NAMES)
def test_parsed_values_match_the_solver_metadata(name: str) -> None:
    """Version, status, objective, bound, walltime and size must match what OR-Tools reported.

    ``index.json`` was written by the collector from the ``CpSolverResponse`` object, so a
    mismatch means the parser reads the log differently than the solver meant it. Walltime is
    compared with a 5% tolerance because the log prints it rounded.
    """
    logs, index = load_corpus()
    log = parse_log(logs[name])
    meta = index[name]
    response, model = log.response, log.initial_model
    assert response is not None and model is not None

    if "ortools_version" in meta:  # three early runs predate the field
        assert log.solver is not None and log.solver.version is not None
        assert log.solver.version.value == meta["ortools_version"]
    if "status" in meta:
        assert response.status is not None
        assert response.status.value == meta["status"]
    for key, value in (
        ("objective", response.objective),
        ("best_bound", response.best_bound),
    ):
        if key in meta:
            assert value is not None, key
            assert value.value == pytest.approx(meta[key], rel=1e-6)
    if "wall_time" in meta and response.walltime is not None:
        assert response.walltime.value == pytest.approx(meta["wall_time"], rel=0.05, abs=0.05)
    if "num_variables" in meta:
        assert model.num_variables is not None
        assert model.num_variables.value == meta["num_variables"]
    workers = (meta.get("parameters") or {}).get("num_workers")
    if workers and log.solver is not None and log.solver.parameters is not None:
        assert log.solver.parameters.value.get("num_workers", workers) == workers


@pytest.mark.parametrize("name", NAMES[::10])
def test_json_round_trip_on_a_sample(name: str) -> None:
    """Serialization is checked on every tenth log; the full corpus would only be slower."""
    logs, _ = load_corpus()
    log = parse_log(logs[name])
    assert CpSatLog.model_validate_json(log.model_dump_json()) == log

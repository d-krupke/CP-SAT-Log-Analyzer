"""The analysis must survive every log of the committed benchmark corpus (295 real logs).

Created 2026-09-06: the insight triggers and the knowledge texts were audited against the
local corpus by hand (see ``benchmarks/README.md``); this test keeps that audit alive.
Its job is coverage, not exact values - the hand-written logs in ``test_analysis.py``
pin down single triggers, while this one makes sure no real log makes ``analyze`` raise,
makes a trigger blow up, or shows a worker the knowledge base cannot name.

Skipped entirely when the archive is not present; see ``v2/corpus/README.md``.
"""

from __future__ import annotations

import logging

import pytest
from cpsatlog import parse_log

from app.analysis import analyze

from .corpus import ARCHIVE, corpus_names, load_corpus

pytestmark = pytest.mark.skipif(not ARCHIVE.is_file(), reason=f"no corpus at {ARCHIVE}")

NAMES = corpus_names()


@pytest.mark.parametrize("name", NAMES)
def test_analysis_runs_and_renders(name: str, caplog: pytest.LogCaptureFixture) -> None:
    """Every log analyzes, and every insight/metric it produces is presentable.

    ``build_insights`` swallows a trigger that raises so that one bad box cannot take down the
    whole analysis; the warning it logs instead is turned back into a failure here, because a
    trigger meeting an unexpected log shape is exactly what real logs are for.
    """
    logs, _ = load_corpus()
    with caplog.at_level(logging.WARNING, logger="app.insights.base"):
        analysis = analyze(parse_log(logs[name]))
    assert caplog.records == [], (name, [r.getMessage() for r in caplog.records])
    for insight in analysis.insights:
        assert insight.title, name
        assert insight.text.strip(), (name, insight.title)
        assert "{" not in insight.text, (name, insight.title, insight.text)
        assert insight.level in {"info", "good", "warn", "bad"}, (name, insight.level)
    for metric in analysis.metrics:
        assert metric.label, name
    titles = [insight.title for insight in analysis.insights]
    assert len(titles) == len(set(titles)), (name, titles)


@pytest.mark.parametrize("name", NAMES)
def test_every_worker_in_the_log_is_documented(name: str) -> None:
    """Each subsolver the analysis lists gets a description from ``subsolvers.toml``.

    New OR-Tools versions add workers and rename others; when that happens the UI would
    silently show an undocumented name, so the corpus is the tripwire.
    """
    logs, _ = load_corpus()
    analysis = analyze(parse_log(logs[name]))
    undocumented = [s.name for s in analysis.subsolvers if not s.description]
    assert undocumented == [], (name, undocumented)


@pytest.mark.parametrize("name", NAMES)
def test_overridden_parameters_are_documented(name: str) -> None:
    """Parameters printed in the header are either documented or explicitly marked unknown."""
    logs, _ = load_corpus()
    analysis = analyze(parse_log(logs[name]))
    for parameter in analysis.parameters:
        assert parameter.known, (name, parameter.name)
        assert parameter.doc.strip() or parameter.advice, (name, parameter.name)


def test_the_only_hint_lines_in_the_corpus_are_vacuous_ones() -> None:
    """None of the 295 benchmark runs passed a hint, so none may be reported as hinted.

    Eleven of them (sudoku, one dominating set instance) nevertheless print `The solution hint
    is complete and is feasible.`, because presolve fixed every variable and the check then
    trivially succeeds. This guards the rule that recognizes those lines as vacuous - without
    it the analyzer would tell users about a hint they never gave.
    """
    logs, _ = load_corpus()
    hinted, vacuous = [], []
    for name, text in logs.items():
        report = analyze(parse_log(text)).hint
        if report.provided:
            hinted.append(name)
        elif report.status == "vacuous":
            vacuous.append(name)
    assert hinted == []
    assert len(vacuous) == 11, vacuous

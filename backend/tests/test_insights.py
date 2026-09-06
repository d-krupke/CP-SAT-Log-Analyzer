"""The insight trigger framework (``app.insights``).

Created 2026-09 when the insight rules moved from ``knowledge/insights.toml``
into one class per box. These tests cover the framework rather than single
triggers - discovery, ordering, the invariants every box must satisfy and the
containment of a trigger that raises. What an individual trigger says about a
given log is pinned down in ``test_analysis.py``, ``test_broken.py`` and
``test_hints.py``; that every trigger survives 295 real logs is
``test_corpus.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from cpsatlog import parse_log

from app.analysis import analyze, build_progress
from app.hints import build_hint_report
from app.insights import LEVELS, Context, Insight, Trigger, all_triggers, base, build_insights

TRIGGER_DIR = Path(base.__file__).parent / "triggers"
HEALTHY = (
    Path(__file__).resolve().parents[2] / "example_logs" / "915_jobshop_8workers.txt"
).read_text()


class RaisingTrigger(Trigger):
    """Used by the containment test below; removed from the registry right away."""

    title = "Never shown"

    def check(self, ctx: Context) -> Insight | None:
        raise RuntimeError("boom")


base.TRIGGERS.remove(RaisingTrigger)


def context(text: str) -> Context:
    log = parse_log(text)
    return Context(log=log, progress=build_progress(log), hint=build_hint_report(log))


def test_every_module_under_triggers_is_loaded() -> None:
    """Discovery is by import of the package directory: dropping in a file is enough.

    The check is indirect on purpose - it compares the modules on disk with the modules the
    loaded trigger classes come from, so a file that defines no trigger (or one that is never
    imported) is noticed.
    """
    on_disk = {p.stem for p in TRIGGER_DIR.glob("*.py") if p.stem != "__init__"}
    loaded = {type(t).__module__.rsplit(".", 1)[-1] for t in all_triggers()}
    assert loaded == on_disk


def test_triggers_have_the_properties_the_ui_relies_on() -> None:
    """A box without a title, with an unknown level or with a duplicate name is a bug."""
    triggers = all_triggers()
    assert len(triggers) > 20
    for trigger in triggers:
        assert trigger.title, trigger.key
        assert trigger.level in LEVELS, (trigger.key, trigger.level)
    keys = [t.key for t in triggers]
    titles = [t.title for t in triggers]
    assert len(set(keys)) == len(keys)
    assert len(set(titles)) == len(titles), "titles identify a box in the UI, keep them distinct"


def test_triggers_are_returned_in_display_order() -> None:
    """Log-quality boxes come first; everything below them is derived from that log."""
    orders = [t.order for t in all_triggers()]
    assert orders == sorted(orders)
    assert all_triggers()[0].order == 10


def test_fire_removes_the_indentation_of_the_source() -> None:
    """Texts are written as indented triple-quoted strings; Markdown would read that as code."""

    class Indented(Trigger):
        title = "Indented"

        def check(self, ctx: Context) -> Insight | None:
            return self.fire(
                """
                First line.
                Second line.
                """,
                [7],
            )

    base.TRIGGERS.remove(Indented)
    insight = Indented().check(context(HEALTHY))
    assert insight is not None
    assert insight.text == "First line.\nSecond line."
    assert insight.lines == [7]
    assert insight.title == "Indented"
    assert insight.level == "info"


def test_a_trigger_that_raises_is_skipped_with_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """One broken box must not cost the reader the whole analysis - but must be visible."""
    monkeypatch.setattr(base, "all_triggers", lambda: [RaisingTrigger()])
    log = parse_log(HEALTHY)
    with caplog.at_level(logging.WARNING, logger="app.insights.base"):
        insights = build_insights(log, build_progress(log), build_hint_report(log))
    assert insights == []
    assert "raising_trigger" in caplog.text


def test_a_healthy_log_produces_boxes_with_evidence_lines() -> None:
    """End to end: the boxes of a real log point at lines that exist in it."""
    log = parse_log(HEALTHY)
    insights = analyze(log).insights
    assert insights
    for insight in insights:
        assert insight.lines, insight.title
        assert all(1 <= line <= log.num_lines for line in insight.lines), insight.title

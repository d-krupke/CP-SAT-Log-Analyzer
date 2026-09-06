"""What the analysis makes of broken, incomplete and foreign logs.

Created 2026-09-06 together with the parser's robustness tests. Two things matter here:
``analyze()` must not raise on any of these inputs, and the reader must be *told* what is
wrong instead of silently getting an analysis of half a log. The four log-quality triggers
(``app/insights/triggers/log_quality.py``) are that signal; they are asserted per case below,
including that they stay quiet on a healthy log.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cpsatlog import parse_log
from fastapi.testclient import TestClient

from app.analysis import analyze
from app.insights.triggers.log_quality import (
    HeadMissing,
    LogTruncated,
    NotACpSatLog,
    UnrecognizedLines,
)
from app.main import app

HEALTHY = (
    Path(__file__).resolve().parents[3] / "example_logs" / "915_jobshop_8workers.txt"
).read_text()
client = TestClient(app)

NOT_A_LOG = "Hello, this is not a log at all.\nJust some text somebody pasted.\n"


def truncate(text: str, fraction: float) -> str:
    lines = text.split("\n")
    return "\n".join(lines[: int(len(lines) * fraction)])


def drop_head(text: str, lines: int) -> str:
    return "\n".join(text.split("\n")[lines:])


def interleave(text: str, every: int) -> str:
    out: list[str] = []
    for i, line in enumerate(text.split("\n")):
        out.append(line)
        if i % every == 0:
            out.append(">>> my own print")
    return "\n".join(out)


DAMAGED = {
    "not_a_log": NOT_A_LOG,
    "whitespace": "   \n\n\t\n",
    "truncated_10%": truncate(HEALTHY, 0.10),
    "truncated_50%": truncate(HEALTHY, 0.50),
    "head_dropped": drop_head(HEALTHY, 40),
    "clipped": "\n".join(line[:38] for line in HEALTHY.split("\n")),
    "prefixed": "\n".join("2026-09-06 10:00:00 INFO | " + ln for ln in HEALTHY.split("\n")),
    "own_prints": interleave(HEALTHY, 37),
    "two_runs": HEALTHY + "\n" + HEALTHY,
}


@pytest.mark.parametrize("name", list(DAMAGED))
def test_analysis_survives_damaged_logs(name: str) -> None:
    """No exception, and every insight text still renders (no leftover format fields)."""
    analysis = analyze(parse_log(DAMAGED[name]))
    for insight in analysis.insights:
        assert insight.title and insight.text, name
        assert "{" not in insight.text, (name, insight.title)
        assert insight.level in {"info", "good", "warn", "bad"}, name
    for metric in analysis.metrics:
        assert metric.label and metric.value, name


@pytest.mark.parametrize("name", list(DAMAGED))
def test_api_parses_damaged_logs(name: str) -> None:
    """The HTTP layer must answer 200 with a serializable analysis, not a 500."""
    if not DAMAGED[name].strip():
        assert client.post("/api/parse", json={"text": DAMAGED[name]}).status_code == 400
        return
    response = client.post("/api/parse", json={"text": DAMAGED[name]})
    assert response.status_code == 200, name
    body = response.json()
    assert body["log"]["num_lines"] > 0


def test_empty_log_is_rejected() -> None:
    assert client.post("/api/parse", json={"text": ""}).status_code == 400
    assert client.post("/api/parse", json={"text": "   \n\n"}).status_code == 400


def titles_of(text: str) -> set[str]:
    return {i.title for i in analyze(parse_log(text)).insights}


def test_foreign_text_says_it_is_not_a_cpsat_log() -> None:
    """Pasting the wrong file must produce a clear statement, not an empty analysis."""
    assert NotACpSatLog.title in titles_of(NOT_A_LOG)


def test_truncated_log_is_reported_as_incomplete() -> None:
    """Without the response summary the numbers below are partial; say so."""
    titles = titles_of(truncate(HEALTHY, 0.5))
    assert LogTruncated.title in titles
    assert NotACpSatLog.title not in titles


def test_missing_head_is_reported() -> None:
    """Only the tail was pasted: version, parameters and the model are unknown."""
    titles = titles_of(drop_head(HEALTHY, 40))
    assert HeadMissing.title in titles
    assert LogTruncated.title not in titles  # the response is there


def test_unrecognized_lines_are_reported_with_their_count() -> None:
    """Own prints inside the log are kept, highlighted and counted."""
    log = parse_log(interleave(HEALTHY, 37))
    unparsed = sum(len(block.lines) for block in log.unparsed)
    assert unparsed > 0
    insight = next(i for i in analyze(log).insights if i.title == UnrecognizedLines.title)
    assert str(unparsed) in insight.text
    assert insight.lines and insight.lines[0] == log.unparsed[0].span.start


def test_a_healthy_log_reports_no_log_problem() -> None:
    """The four log-quality triggers must stay quiet on a complete, fully parsed log."""
    titles = titles_of(HEALTHY)
    for trigger in (NotACpSatLog, LogTruncated, HeadMissing, UnrecognizedLines):
        assert trigger.title not in titles

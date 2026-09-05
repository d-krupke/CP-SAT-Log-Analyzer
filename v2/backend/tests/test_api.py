"""API tests for the backend: every endpoint responds and the analysis is grounded.

We parse the bundled example logs through the HTTP layer so that JSON
serialisation of the parser models and of the analysis is exercised end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

EXAMPLES = Path(__file__).resolve().parents[3] / "example_logs"
client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_examples_listed_and_readable() -> None:
    listed = client.get("/api/examples").json()
    names = {e["name"] for e in listed}
    assert "98_07" in names and "915_01" in names
    text = client.get("/api/examples/98_07").json()["text"]
    assert "CpSolverResponse summary" in text
    assert client.get("/api/examples/../etc").status_code == 404
    assert client.get("/api/examples/nope").status_code == 404


def test_parse_rejects_empty() -> None:
    assert client.post("/api/parse", json={"text": "   "}).status_code == 400


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.txt")), ids=lambda p: p.stem)
def test_parse_example(path: Path) -> None:
    """Every example parses via the API; metrics and blocks are line-anchored."""
    res = client.post("/api/parse", json={"text": path.read_text()})
    assert res.status_code == 200, res.text
    body = res.json()
    log, analysis = body["log"], body["analysis"]
    assert log["num_lines"] > 0
    keys = {m["key"] for m in analysis["metrics"]}
    assert {"version", "status"} <= keys
    for m in analysis["metrics"]:
        if m["line"] is not None:
            assert 1 <= m["line"] <= log["num_lines"]
    for ins in analysis["insights"]:
        for line in ins["lines"]:
            assert 1 <= line <= log["num_lines"]


def test_parse_915_analysis() -> None:
    """Concrete expectations for the 9.15 example: maximize, params explained, plot data."""
    body = client.post("/api/parse", json={"text": (EXAMPLES / "915_01.txt").read_text()}).json()
    analysis = body["analysis"]
    assert analysis["progress"]["objective_sense"] == "maximize"
    assert analysis["progress"]["solutions"]
    assert analysis["progress"]["bounds"]
    params = {p["name"]: p for p in analysis["parameters"]}
    assert params["max_time_in_seconds"]["known"] is True
    assert params["max_time_in_seconds"]["advice"]
    assert params["num_workers"]["warning"] is None
    assert any(s["name"] == "fj_restart" and s["solutions"] >= 1 for s in analysis["subsolvers"])


def test_parse_98_07_summary_counter_insight() -> None:
    """98_07: solution returned by a helper -> summary conflicts far below core's; insight fires."""
    body = client.post("/api/parse", json={"text": (EXAMPLES / "98_07.txt").read_text()}).json()
    titles = {i["title"] for i in body["analysis"]["insights"]}
    assert "Summary counters are per worker" in titles


def test_explanations_and_parameters() -> None:
    ex = client.get("/api/explanations").json()
    assert "search_stats" in ex["tables"]
    assert "Conflicts" in ex["tables"]["search_stats"]["columns"]
    assert "conflicts" in ex["response_fields"]
    p = client.get("/api/parameters/num_search_workers").json()
    assert p["known"] is True
    assert "Deprecated" in p["advice"]
    assert client.get("/api/parameters/does_not_exist").json()["known"] is False


def test_progress_ends_with_response_bound() -> None:
    """93_01 proves optimality without a final bound line; the response bound closes the curve."""
    body = client.post("/api/parse", json={"text": (EXAMPLES / "93_01.txt").read_text()}).json()
    bounds = body["analysis"]["progress"]["bounds"]
    assert bounds[-1]["value"] == 15
    assert bounds[-1]["time"] > bounds[-2]["time"]


def test_satisfaction_problem_has_no_bound_curve() -> None:
    """98_05 is a satisfaction problem: the response's 'best_bound: 0' must not create a curve."""
    body = client.post("/api/parse", json={"text": (EXAMPLES / "98_05.txt").read_text()}).json()
    assert body["analysis"]["progress"]["bounds"] == []

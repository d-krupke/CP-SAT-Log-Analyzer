"""The deployment chrome (``app.site``): issue link and the operator's legal pages.

Created 2026-09 with the public deployment. The point of these tests is that the
app stays neutral by default - an instance that configures nothing must not
claim an imprint it does not have - and that a misconfigured file is reported
instead of rendering as a broken link.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.site import DEFAULT_ISSUE_URL, site_config

client = TestClient(app)
ENV = (
    "ISSUE_URL",
    "IMPRINT_URL",
    "IMPRINT_FILE",
    "IMPRINT_LABEL",
    "PRIVACY_URL",
    "PRIVACY_FILE",
    "PRIVACY_LABEL",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from an unconfigured deployment, whatever the developer has set."""
    for name in ENV:
        monkeypatch.delenv(name, raising=False)


def test_an_unconfigured_deployment_offers_only_the_issue_link() -> None:
    """The project ships no imprint: legal pages belong to whoever operates the instance."""
    config = site_config()
    assert config.issue_url == DEFAULT_ISSUE_URL
    assert config.pages == []


def test_urls_are_taken_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The common deployment: link to pages that already exist on the operator's site."""
    monkeypatch.setenv("ISSUE_URL", "https://example.org/bugs")
    monkeypatch.setenv("IMPRINT_URL", "https://example.org/impressum")
    monkeypatch.setenv("PRIVACY_URL", "https://example.org/datenschutz")
    monkeypatch.setenv("PRIVACY_LABEL", "Datenschutz")
    config = site_config()
    assert config.issue_url == "https://example.org/bugs"
    assert [(p.key, p.label, p.url) for p in config.pages] == [
        ("imprint", "Impressum", "https://example.org/impressum"),
        ("privacy", "Datenschutz", "https://example.org/datenschutz"),
    ]
    assert all(p.markdown is None for p in config.pages)


def test_a_markdown_file_is_served_as_page_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A mounted file is read per request, so editing it needs no restart."""
    page = tmp_path / "impressum.md"
    page.write_text("# Impressum\n\nAngaben gemäß § 5 DDG.\n")
    monkeypatch.setenv("IMPRINT_FILE", str(page))
    assert site_config().pages[0].markdown == "# Impressum\n\nAngaben gemäß § 5 DDG."
    page.write_text("# Impressum\n\nNeue Anschrift.\n")
    assert site_config().pages[0].markdown.endswith("Neue Anschrift.")


def test_a_url_wins_over_a_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file = tmp_path / "impressum.md"
    file.write_text("ignored")
    monkeypatch.setenv("IMPRINT_FILE", str(file))
    monkeypatch.setenv("IMPRINT_URL", "https://example.org/impressum")
    assert site_config().pages[0].url == "https://example.org/impressum"
    assert site_config().pages[0].markdown is None


@pytest.mark.parametrize("content", ["", "   \n"])
def test_an_empty_or_missing_file_is_reported_not_shown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture, content: str
) -> None:
    """A legal link that opens an empty dialog is worse than no link: say so in the log."""
    file = tmp_path / "impressum.md"
    file.write_text(content)
    monkeypatch.setenv("IMPRINT_FILE", str(file))
    with caplog.at_level(logging.WARNING, logger="app.site"):
        assert site_config().pages == []
    assert "IMPRINT_FILE" in caplog.text

    caplog.clear()
    monkeypatch.setenv("IMPRINT_FILE", str(tmp_path / "does-not-exist.md"))
    with caplog.at_level(logging.WARNING, logger="app.site"):
        assert site_config().pages == []
    assert "IMPRINT_FILE" in caplog.text


def test_empty_variables_count_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """``IMPRINT_URL: "${IMPRINT_URL:-}"`` in a compose file sets an empty string."""
    monkeypatch.setenv("ISSUE_URL", "")
    monkeypatch.setenv("IMPRINT_URL", "  ")
    config = site_config()
    assert config.issue_url == DEFAULT_ISSUE_URL
    assert config.pages == []


def test_the_endpoint_returns_the_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPRINT_URL", "https://example.org/impressum")
    body = client.get("/api/site").json()
    assert body["issue_url"] == DEFAULT_ISSUE_URL
    assert body["pages"] == [
        {
            "key": "imprint",
            "label": "Impressum",
            "url": "https://example.org/impressum",
            "markdown": None,
        }
    ]

"""Deployment-specific chrome: the issue link and the operator's legal pages.

Created 2026-09 for hosting the analyzer publicly. Running a public website in
Germany (and most of the EU) requires an imprint and a privacy statement, but
those belong to whoever *operates* the instance, not to the project - so the
app ships without them and picks them up from the environment.

Everything here is optional; with no variables set the app looks exactly as
before, minus nothing. Configure a deployment with:

===========================  ==================================================
``ISSUE_URL``                where "Report issue" points (default: this repo)
``IMPRINT_URL``              link out to an existing imprint page, or ...
``IMPRINT_FILE``             ... a Markdown file shown in a dialog
``IMPRINT_LABEL``            link text (default ``Impressum``)
``PRIVACY_URL``              link out to an existing privacy policy, or ...
``PRIVACY_FILE``             ... a Markdown file shown in a dialog
``PRIVACY_LABEL``            link text (default ``Privacy``)
===========================  ==================================================

``*_URL`` wins over ``*_FILE`` when both are set. Files are read per request, so
a mounted file can be edited without restarting the container; an unreadable one
is logged and its link is omitted rather than shown broken - check the container
log after a deployment, or run ``python -m app.site`` to print the resolved
configuration.

See ``docs/deployment.md`` for the docker-compose side.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_ISSUE_URL = "https://github.com/d-krupke/CP-SAT-Log-Analyzer/issues"

logger = logging.getLogger(__name__)


class SitePage(BaseModel):
    """One extra link in the top bar: either an outgoing link or a Markdown dialog."""

    key: str
    label: str
    url: str | None = Field(default=None, description="External page; opens in a new tab")
    markdown: str | None = Field(default=None, description="Shown in a dialog when no url")


class SiteConfig(BaseModel):
    """What the frontend needs to know about *this* deployment."""

    issue_url: str = DEFAULT_ISSUE_URL
    pages: list[SitePage] = Field(default_factory=list)


def _env(name: str) -> str | None:
    """Environment variable, treating "set but empty" as unset (compose does that a lot)."""
    value = os.environ.get(name, "").strip()
    return value or None


def _page(key: str, default_label: str) -> SitePage | None:
    prefix = key.upper()
    label = _env(f"{prefix}_LABEL") or default_label
    url = _env(f"{prefix}_URL")
    if url:
        return SitePage(key=key, label=label, url=url)
    path = _env(f"{prefix}_FILE")
    if not path:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("%s_FILE is set but unreadable, link omitted: %s", prefix, exc)
        return None
    if not text:
        logger.warning("%s_FILE is empty, link omitted: %s", prefix, path)
        return None
    return SitePage(key=key, label=label, markdown=text)


def site_config() -> SiteConfig:
    """Read the deployment configuration from the environment (per request; nothing is cached)."""
    pages = [_page("imprint", "Impressum"), _page("privacy", "Privacy")]
    return SiteConfig(
        issue_url=_env("ISSUE_URL") or DEFAULT_ISSUE_URL,
        pages=[page for page in pages if page is not None],
    )


def main() -> int:
    """``python -m app.site``: print what this environment resolves to."""
    config = site_config()
    print(json.dumps(config.model_dump(), indent=2))
    for page in config.pages:
        print(f"# {page.key}: {'link to ' + page.url if page.url else 'dialog from file'}")
    if not config.pages:
        print("# no legal pages configured (IMPRINT_URL/IMPRINT_FILE, PRIVACY_URL/PRIVACY_FILE)")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())

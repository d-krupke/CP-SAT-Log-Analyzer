"""Serving the built frontend: the mount must not hand out the filesystem.

Created 2026-09-07 after a review found that the hand-written catch-all this
replaced joined the request path onto ``STATIC_DIR`` and served whatever came
out. The path reaches the app percent-decoded, so ``/..%2Fsecret.txt`` climbed
out of the static directory and returned any file the process could read - on
the public deployment, which is the one configuration that sets ``STATIC_DIR``.
A browser normalizes a literal ``/../`` away, which is why this was invisible in
manual use; the encoded forms below are the ones that arrive intact.

``StaticFiles`` refuses those itself, so these tests are here to keep the mount
from being replaced by something hand-written again.

The mount only exists when ``STATIC_DIR`` names a directory, and it is read at
import time, so these tests reload ``app.main`` against a temporary one.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main


@pytest.fixture
def static_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A client for an instance serving a built frontend, with a secret next to it."""
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>shell</html>")
    (root / "assets" / "app.js").write_text("// bundle")
    (tmp_path / "secret.txt").write_text("TOP SECRET")

    monkeypatch.setenv("STATIC_DIR", str(root))
    importlib.reload(app.main)
    try:
        with TestClient(app.main.app) as client:
            yield client
    finally:
        # Other modules hold a client bound to the app object built without
        # STATIC_DIR; put the module back the way they found it.
        monkeypatch.delenv("STATIC_DIR")
        importlib.reload(app.main)


def test_a_built_file_is_served(static_client: TestClient) -> None:
    """The happy path the route exists for."""
    assert static_client.get("/assets/app.js").text == "// bundle"


def test_the_root_serves_the_shell(static_client: TestClient) -> None:
    """``html=True``: the directory itself answers with index.html."""
    response = static_client.get("/")
    assert response.status_code == 200
    assert response.text == "<html>shell</html>"


def test_an_unknown_path_is_a_404(static_client: TestClient) -> None:
    """There are no client-side routes here - deep links are ``/?example=...``, a
    query on ``/`` - so a path with no file behind it is simply not found. The
    catch-all this replaced answered every one of them with the shell."""
    assert static_client.get("/whatever/deep/link").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/..%2Fsecret.txt",
        "/%2e%2e/secret.txt",
        "/..%2F..%2Fetc/hostname",
        "/assets/../../secret.txt",
    ],
)
def test_the_mount_cannot_climb_out_of_the_static_directory(
    static_client: TestClient, path: str
) -> None:
    """Every escape resolves outside the root and is refused.

    The body is asserted as well as the status: the bug this guards was a 200
    that happened to contain the file.
    """
    response = static_client.get(path)
    assert "TOP SECRET" not in response.text
    assert response.status_code == 404

"""FastAPI application of the CP-SAT Log Analyzer.

Run locally with ``uv run uvicorn app.main:app --reload`` (from ``backend``)
or via ``docker compose up`` (see ``docker-compose.yml``). Endpoints:

- ``POST /api/parse``            body ``{"text": "<log>"}`` -> parsed log + analysis
- ``GET  /api/examples``         list of bundled example logs
- ``GET  /api/examples/{name}``  raw text of an example
- ``GET  /api/explanations``     static explanation texts (blocks, tables, columns, ...)
- ``GET  /api/parameters/{name}`` documentation of one solver parameter
- ``GET  /api/site``             deployment chrome: issue link, imprint, privacy
- ``GET  /api/health``

If ``STATIC_DIR`` points to a built frontend, it is served at ``/`` so a single
container can host the whole app.
"""

from __future__ import annotations

import os
from pathlib import Path

from cpsat_logutils import CpSatLog, parse_log
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .analysis import Analysis, analyze
from .examples import ExampleInfo, list_examples, read_example
from .explanations import Explanations, all_explanations
from .parameters import ParameterInfo, describe_parameter
from .site import SiteConfig, site_config

MAX_LOG_BYTES = 20 * 1024 * 1024

app = FastAPI(title="CP-SAT Log Analyzer", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    text: str = Field(description="Raw CP-SAT log text.")


class ParseResponse(BaseModel):
    log: CpSatLog
    analysis: Analysis


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    if len(req.text.encode("utf-8", errors="replace")) > MAX_LOG_BYTES:
        raise HTTPException(413, "Log too large.")
    if not req.text.strip():
        raise HTTPException(400, "Empty log.")
    log = parse_log(req.text)
    return ParseResponse(log=log, analysis=analyze(log))


@app.get("/api/examples", response_model=list[ExampleInfo])
def examples() -> list[ExampleInfo]:
    return list_examples()


@app.get("/api/examples/{name}")
def example(name: str) -> dict[str, str]:
    text = read_example(name)
    if text is None:
        raise HTTPException(404, "Unknown example.")
    return {"name": name, "text": text}


@app.get("/api/explanations", response_model=Explanations)
def explanations() -> Explanations:
    return all_explanations()


@app.get("/api/parameters/{name}", response_model=ParameterInfo)
def parameter(name: str) -> ParameterInfo:
    return describe_parameter(name, None)


@app.get("/api/site", response_model=SiteConfig)
def site() -> SiteConfig:
    """Where "Report issue" points, plus whatever legal pages this deployment configured."""
    return site_config()


STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/nonexistent"))
if STATIC_DIR.is_dir():
    # The built frontend, so that a single container can host the whole app.
    #
    # `frontend()` registers low-priority routes: the API is matched first no
    # matter where this line sits, which a `mount("/")` cannot promise - a mount
    # swallows every route declared after it, and this is the end of the file.
    # It also does its own containment check, which is what this used to get
    # wrong (see tests/test_static.py).
    #
    # `fallback=None` because there is nothing to fall back to: deep links here
    # are `/?example=...`, a query on `/`, so a path with no file behind it is
    # genuinely not found. The default would answer a browser navigating to one
    # with the shell, which is right for client-side routing and a lie here.
    app.frontend("/", directory=STATIC_DIR, fallback=None)

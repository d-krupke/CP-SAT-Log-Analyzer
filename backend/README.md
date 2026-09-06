# Backend

FastAPI app: parses a log with [`cpsatlog`](../cpsatlog/README.md), derives the analysis
(tiles, insight boxes, progress series, subsolver attribution, hint report) and serves the
texts of the [knowledge base](../knowledge/README.md).

```bash
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run python -m app.knowledge   # every knowledge file parses and has its sections
```

See [`docs/architecture.md`](../docs/architecture.md#backend---analysis-and-explanations) for
what each module is responsible for, and [`docs/development.md`](../docs/development.md) for
the test suites.

## HTTP API

The frontend is the only client, but the API is plain JSON and usable on its own.

| Endpoint | Returns |
| --- | --- |
| `POST /api/parse` `{"text": "<log>"}` | `{"log": <CpSatLog JSON>, "analysis": {...}}` - the parsed log with line numbers plus tiles, insights, progress series and subsolver attribution |
| `GET /api/examples` | the bundled example logs with a curated description and a derived one-line summary |
| `GET /api/examples/{name}` | `{"text": "<log>"}` for one example |
| `GET /api/explanations` | every text from `knowledge/`: blocks, cards, tables, columns, response fields, subsolvers, constraints, messages |
| `GET /api/parameters/{name}` | documentation, advice and warnings for one solver parameter |
| `GET /api/site` | the deployment chrome: where *Report issue* points and which legal pages this instance configured (see [deployment.md](../docs/deployment.md#legal-pages-imprint-and-privacy)) |
| `GET /api/health` | `{"status": "ok"}` |

Requests are limited to 20 MB of log text (`MAX_LOG_BYTES` in `app/main.py`); nothing is
stored on the server.

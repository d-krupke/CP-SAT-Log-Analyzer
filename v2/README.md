# CP-SAT Log Analyzer v2

The current implementation, in five parts:

| Part | Path | What it is |
| --- | --- | --- |
| Parser library | [`cpsatlog/`](cpsatlog/README.md) | Standalone Python library (installable, pydantic models, every value carries its log line). |
| Backend | `backend/` | FastAPI app: parses logs with `cpsatlog`, adds derived analysis, insights, explanations and parameter docs. |
| Frontend | [`frontend/`](frontend/README.md) | React + Vite + Plotly UI: analysis on the left, raw log on the right, linked both ways. |
| Knowledge | [`knowledge/`](knowledge/README.md) | Plain TOML with every explanation, parameter advice, subsolver description and insight threshold. Editable without programming. |
| Test corpus | [`corpus/`](corpus/README.md) | 295 real CP-SAT logs, compressed, used by the parser and backend test suites. |

The Streamlit app in the repository root is the previous implementation and is left untouched;
see [`docs/legacy-streamlit-app.md`](../docs/legacy-streamlit-app.md).

## Where to go

| Task | Read |
| --- | --- |
| Run it locally, run the tests, edit the explanations | [`docs/development.md`](../docs/development.md) |
| Deploy it for other people | [`docs/deployment.md`](../docs/deployment.md) |
| Understand how the parts fit together | [`docs/architecture.md`](../docs/architecture.md) |

Quick start:

```bash
cd v2
docker compose up --build
# open http://localhost:8080
```

## HTTP API

The frontend is the only client, but the API is plain JSON and usable on its own.

| Endpoint | Returns |
| --- | --- |
| `POST /api/parse` `{"text": "<log>"}` | `{"log": <CpSatLog JSON>, "analysis": {...}}` - the parsed log with line numbers plus tiles, insights, progress series and subsolver attribution |
| `GET /api/examples` | the bundled example logs with a curated description and a derived one-line summary |
| `GET /api/examples/{name}` | `{"text": "<log>"}` for one example |
| `GET /api/explanations` | every text from `knowledge/`: blocks, cards, tables, columns, response fields, subsolvers, constraints, messages |
| `GET /api/parameters/{name}` | documentation, advice and warnings for one solver parameter |
| `GET /api/health` | `{"status": "ok"}` |

Requests are limited to 20 MB of log text (`MAX_LOG_BYTES` in `backend/app/main.py`); nothing
is stored on the server.

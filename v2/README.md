# CP-SAT Log Analyzer v2

Rewrite of the analyzer as three parts:

| Part | Path | What it is |
| --- | --- | --- |
| Parser library | `cpsatlog/` | Standalone Python library (`pip install`-able, pydantic models, every value carries its log line). See its README. |
| Backend | `backend/` | FastAPI app: parses logs with `cpsatlog`, adds derived analysis, explanations and parameter docs. |
| Frontend | `frontend/` | React + Vite + Plotly UI: analysis on the left, raw log on the right, linked both ways. |

The old Streamlit app in the repository root is untouched.

## Run with Docker

```bash
cd v2
docker compose up --build
# open http://localhost:8080
```

The frontend container (nginx) serves the built UI and proxies `/api` to the backend container.

## Local development

Backend (uv, Python 3.12):

```bash
cd v2/backend
uv sync --python 3.12
uv run uvicorn app.main:app --reload --port 8000
uv run pytest && uv run ruff check . && uv run ty check app
```

Frontend (Vite dev server with `/api` proxied to the backend on port 8000; set `VITE_PROXY_TARGET` to change):

```bash
cd v2/frontend
npm install
npm run dev        # http://localhost:5173  (add ?example=98_02 to deep-link an example)
npm run build      # tsc + vite build
npm run lint
```

Parser library:

```bash
cd v2/cpsatlog
uv sync --python 3.12
uv run pytest && uv run ruff check . && uv run ty check
```

## API

- `POST /api/parse` `{"text": "<log>"}` → `{"log": <CpSatLog JSON>, "analysis": {...}}`
- `GET /api/examples`, `GET /api/examples/{name}` (from `example_logs/` or `EXAMPLE_LOGS_DIR`)
- `GET /api/explanations` static explanation texts (blocks, tables, columns, response fields, subsolvers)
- `GET /api/parameters/{name}` documentation of a solver parameter (generated from `sat_parameters.proto`)
- Set `STATIC_DIR` to a built frontend to serve everything from the backend alone.

## Updating for a new OR-Tools version

1. Add a fresh log to `example_logs/` (the parser test suite parses every file there).
2. Run the parser tests; unrecognised sections show up in `log.unparsed` / as test failures.
3. Extend the parser (`cpsatlog/src/cpsatlog/parsers/`), add explanations for new tables/columns in `backend/app/explanations.py`.
4. Regenerate the parameter docs: `uv run python tools/extract_sat_parameters.py /path/to/or-tools/ortools/sat/sat_parameters.proto` (in `backend/`).

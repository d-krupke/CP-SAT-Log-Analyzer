# Development

Everything described here lives on `main`. The legacy Streamlit app lives on the `legacy`
branch and is frozen; it is documented there.

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22+, and Docker if you
want to run the whole stack.

## The two projects

```sh
cd backend                        # FastAPI app
uv sync --python 3.12
uv run uvicorn app.main:app --reload --port 8000
uv run pytest && uv run ruff check . && uv run ty check app

cd frontend                       # React + Vite + Plotly
npm install
npm run dev        # http://localhost:5173, /api proxied to port 8000
npm run build      # tsc + vite build
npm run lint
```

The dev server proxies `/api` to `http://localhost:8000`; set `VITE_PROXY_TARGET` to point
somewhere else. `?example=915_01` deep-links an example.

The backend must stay clean under `ruff` and `ty`; files are kept small (~200-300 lines, a
split is due past ~500).

Reading the log is not done here: `parse_log` comes from
[cpsat-logutils](https://github.com/d-krupke/cpsat-logutils), an ordinary dependency in `backend/pyproject.toml`. To work on the
parser and the analyzer at once, clone that repository next to this one and point the backend
at it with `uv add --editable ../cpsat-logutils`, then revert that before committing.

## Tests

The parser has its own suite in [cpsat-logutils](https://github.com/d-krupke/cpsat-logutils) (units, every example log, the 295-log
corpus, damaged input, hint wordings). What runs here:

| Suite | What it covers |
| --- | --- |
| `backend/tests/test_api.py` | every endpoint, every example through the HTTP layer |
| `backend/tests/test_analysis.py` | one hand-written log per insight trigger |
| `backend/tests/test_insights.py` | the trigger framework: discovery, display order, the invariants of a box, and that a trigger which raises is contained |
| `backend/tests/test_hints.py` | `build_hint_report`: the verdict per wording, the `complete_hint` evidence, and the vacuous line on a model with no variables |
| `backend/tests/test_broken.py` | analysis and API on damaged logs, and the four log-quality triggers |
| `backend/tests/test_static.py` | serving the built frontend: a real asset, the shell at `/`, a 404 for an unknown path, that the API keeps priority over it, and that no encoded `..` climbs out of the static root |
| `backend/tests/test_site.py` | the deployment chrome: an unconfigured instance shows no legal links, URLs and Markdown files are picked up from the environment, a broken file is reported |
| `backend/tests/test_knowledge.py` | the knowledge base itself: required sections, documented labels, regressions on wrong claims |
| `backend/tests/test_corpus.py` | `analyze()` on all 295 corpus logs: no crash, no trigger blows up, every worker and parameter documented |
| `frontend/e2e/screenshots.spec.ts` | Playwright: the UI renders the examples end to end - it captures the README screenshots (below) and fails when a view breaks |
| `frontend/e2e/mobile.spec.ts` | Playwright at 390 px: one font size in the raw log, stacked panes with a draggable divider, and a top bar that retreats while reading and stays pinned on a wide screen |

Write the test with the change - the corpus suites are what catch the mistakes that only real
logs produce.

## Screenshots for the README

The pictures in the README are generated, never pasted, so that they cannot quietly go stale.
`frontend/e2e/screenshots.spec.ts` drives the real UI with Playwright and writes PNGs into
`docs/screenshots/`:

```sh
cd frontend
npm run screenshots:install   # once: downloads the Chromium build Playwright uses
npm run screenshots           # boots backend + preview server, captures, tears both down
```

Playwright starts everything itself (see `playwright.config.ts`): `uv run uvicorn` on port
8010 and a production `vite build` behind `vite preview` on 4173, both above the ports of a
running `docker compose up` so a capture never collides with your development stack. The input
is a committed example log and the backend keeps no state, so a rerun produces the same images.

Because the spec clicks real controls, it is also a coarse end-to-end smoke test: a view that
throws, a card that got renamed or an example that stopped parsing fails the run.

Regenerate after any visible UI change, and commit the PNGs with it. To add a picture, add a
test - `analyze()` opens an example through its `?example=` deep link, `open()` expands a card
by title, and you photograph either the page or a card locator. `SCREENSHOT_THEME=dark`
captures the dark theme instead.

## Editing explanations, advice and thresholds

CP-SAT domain knowledge is data, not code: `knowledge/*.toml`. Texts are Markdown, insight
thresholds are plain numbers, and `knowledge/README.md` maps each kind of text to its file.
After an edit:

```sh
cd backend && uv run python -m app.knowledge     # every file parses, sections present
uv run pytest tests/test_knowledge.py
```

The running dev server picks up saved files on the next request.

## The benchmark corpus

`benchmarks/` collects real logs by solving public instances (see `benchmarks/README.md`). The
instances stay local; the 295 logs are committed compressed in `corpus/` and drive the two
corpus test suites. After collecting a new batch:

```sh
cd benchmarks
uv run python validate_logs.py   # does the parser understand everything
uv run python mine_patterns.py   # does the knowledge base explain every label
uv run python pack_corpus.py                              # refresh corpus/benchmark_logs.tar.xz
```

## Supporting a new OR-Tools version

1. Solve something with the new version and keep the log.
2. Run the parser tests in the cpsat-logutils checkout against it; unrecognized sections show
   up as `log.unparsed` entries.
3. Extend that package's `parsers/` and `schema/`, release it, and raise the floor in
   `backend/pyproject.toml`.
4. Explain new tables, columns, subsolvers or messages in `knowledge/*.toml`.
5. Regenerate the parameter documentation:
   `cd backend && uv run python tools/extract_sat_parameters.py /path/to/or-tools/ortools/sat/sat_parameters.proto`.
6. Add the log to `example_logs/` if it shows something the current examples do not, otherwise
   to `example_logs/archive/` - both are parsed by the test suite, only the former is offered
   in the UI (`knowledge/examples.toml` holds the descriptions).

## Where things are

See [architecture.md](architecture.md) for the request flow and the responsibilities of each
part, and [deployment.md](deployment.md) for running it in front of other people.

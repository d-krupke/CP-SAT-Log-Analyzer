# Development

Everything in this branch is `v2/`. The legacy Streamlit app lives on the `legacy` branch and
is frozen; it is documented there.

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22+, and Docker if you
want to run the whole stack.

## The three projects

```sh
cd v2/cpsatlog                       # parser library
uv sync --python 3.12
uv run pytest && uv run ruff check . && uv run ty check

cd v2/backend                        # FastAPI app (depends on ../cpsatlog)
uv sync --python 3.12
uv run uvicorn app.main:app --reload --port 8000
uv run pytest && uv run ruff check . && uv run ty check app

cd v2/frontend                       # React + Vite + Plotly
npm install
npm run dev        # http://localhost:5173, /api proxied to port 8000
npm run build      # tsc + vite build
npm run lint
```

The dev server proxies `/api` to `http://localhost:8000`; set `VITE_PROXY_TARGET` to point
somewhere else. `?example=915_01` deep-links an example.

Both Python projects must stay clean under `ruff` and `ty`; files are kept small (~200-300
lines, a split is due past ~500).

## Tests

| Suite | What it covers |
| --- | --- |
| `v2/cpsatlog/tests/test_units.py`, `test_specific.py` | parser internals and exact values of individual example logs |
| `v2/cpsatlog/tests/test_examples.py` | invariants on every log in `example_logs/` **and** `example_logs/archive/`: parses, block index covers every line, JSON round trip |
| `v2/cpsatlog/tests/test_corpus.py` | all 295 corpus logs parse, leave nothing in `log.unparsed`, and match the metadata OR-Tools reported (`v2/corpus/`) |
| `v2/cpsatlog/tests/test_broken.py` | damaged input (truncated, clipped, prefixed, foreign text): no crash, line anchoring intact, unrecognized text kept verbatim |
| `v2/cpsatlog/tests/test_hints.py` | every wording of the solution-hint lines is classified, and a hint line inside the presolve block is still found |
| `v2/cpsatlog/tests/test_latest_version.py` | the parser against a log produced by the installed OR-Tools |
| `v2/backend/tests/test_api.py` | every endpoint, every example through the HTTP layer |
| `v2/backend/tests/test_analysis.py` | one hand-written log per insight trigger |
| `v2/backend/tests/test_insights.py` | the trigger framework: discovery, display order, the invariants of a box, and that a trigger which raises is contained |
| `v2/backend/tests/test_hints.py` | `build_hint_report`: the verdict per wording, the `complete_hint` evidence, and the vacuous line on a model with no variables |
| `v2/backend/tests/test_broken.py` | analysis and API on damaged logs, and the four log-quality triggers |
| `v2/backend/tests/test_site.py` | the deployment chrome: an unconfigured instance shows no legal links, URLs and Markdown files are picked up from the environment, a broken file is reported |
| `v2/backend/tests/test_knowledge.py` | the knowledge base itself: required sections, documented labels, regressions on wrong claims |
| `v2/backend/tests/test_corpus.py` | `analyze()` on all 295 corpus logs: no crash, no trigger blows up, every worker and parameter documented |

Write the test with the change - the corpus suites are what catch the mistakes that only real
logs produce.

## Editing explanations, advice and thresholds

CP-SAT domain knowledge is data, not code: `v2/knowledge/*.toml`. Texts are Markdown, insight
thresholds are plain numbers, and `v2/knowledge/README.md` maps each kind of text to its file.
After an edit:

```sh
cd v2/backend && uv run python -m app.knowledge     # every file parses, sections present
uv run pytest tests/test_knowledge.py
```

The running dev server picks up saved files on the next request.

## The benchmark corpus

`benchmarks/` collects real logs by solving public instances (see `benchmarks/README.md`). The
instances stay local; the 295 logs are committed compressed in `v2/corpus/` and drive the two
corpus test suites. After collecting a new batch:

```sh
cd benchmarks
uv run --project ../v2/cpsatlog python validate_logs.py   # does the parser understand everything
uv run --project ../v2/cpsatlog python mine_patterns.py   # does the knowledge base explain every label
uv run python pack_corpus.py                              # refresh v2/corpus/benchmark_logs.tar.xz
```

## Supporting a new OR-Tools version

1. Solve something with the new version and keep the log.
2. Run the parser tests against it; unrecognized sections show up as `log.unparsed` entries.
3. Extend the parsers in `v2/cpsatlog/src/cpsatlog/parsers/` and the schema in `schema/`.
4. Explain new tables, columns, subsolvers or messages in `v2/knowledge/*.toml`.
5. Regenerate the parameter documentation:
   `cd v2/backend && uv run python tools/extract_sat_parameters.py /path/to/or-tools/ortools/sat/sat_parameters.proto`.
6. Add the log to `example_logs/` if it shows something the current examples do not, otherwise
   to `example_logs/archive/` - both are parsed by the test suite, only the former is offered
   in the UI (`v2/knowledge/examples.toml` holds the descriptions).

## Where things are

See [architecture.md](architecture.md) for the request flow and the responsibilities of each
part, and [deployment.md](deployment.md) for running it in front of other people.

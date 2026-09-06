# Architecture

The v2 analyzer is four parts with one rule between them: **the parser only structures the
log, the knowledge base holds everything a CP-SAT expert knows, and the frontend renders what
the backend derives.** Nothing about CP-SAT semantics is hard-coded in the UI.

```
            example_logs/            v2/knowledge/*.toml
          (10 offered + archive)   (texts, advice, thresholds)
                    |                        |
   raw log  ->  cpsatlog  ->  backend/app  ->  JSON  ->  frontend
              (parse only)   (analysis +            (two linked panes)
                              explanations)
```

## `v2/cpsatlog` - the parser library

Standalone, `pip install`-able, no knowledge of the UI. `parse_log(text)` returns a
`CpSatLog` pydantic model with one attribute per log section (`solver`, `initial_model`,
`presolved_model`, `presolve`, `search`, `stats`, `response`, `messages`, `unparsed`).

The defining property is **line anchoring**: every scalar is a `Loc[T]` carrying `value` and
`line`, every table row knows its line, every section its span, and `log.blocks` is an ordered
index mapping any line back to the section that produced it. That is what lets the UI show the
raw log next to the analysis with both directions clickable.

Sections are parsed by `BlockParser` subclasses in `src/cpsatlog/parsers/` (header, model,
presolve, events, tables, response, ...); a chunk no parser claims lands in `log.unparsed`
instead of being dropped, so a new log format is visible rather than silently mangled. The
same holds for input that is broken rather than new: a truncated, clipped, prefixed or
entirely foreign text parses without raising, keeps its line anchoring, and whatever could not
be used stays in `log.unparsed` with its text. A section that appears twice (two runs in one
file) is reported in `log.warnings` and the copy is kept there too.

## `v2/backend` - analysis and explanations

FastAPI with six endpoints - `parse`, `examples`, `examples/{name}`, `explanations`,
`parameters/{name}`, `health` (see [deployment.md](deployment.md) for the operational view):

| Module | Responsibility |
| --- | --- |
| `analysis.py` | `analyze(log)` -> metrics, progress series, subsolver contributions, insights |
| `metrics.py` | the Overview tiles (version, workers, gap, presolve share, solutions, bound events) and when each turns yellow or red |
| `insights.py` | the 17 rules that produce the coloured boxes; each rule reads its threshold, level, title and text from `insights.toml`. Four of them are about the log rather than the solve (not a CP-SAT log, ends before the response, head missing, unrecognised lines) and are evaluated first |
| `explanations.py` | look-ups into the knowledge base for blocks, tables, columns, response fields, subsolvers, constraints, messages |
| `parameters.py` | documentation for an overridden parameter: generated proto docs plus curated advice and warnings |
| `examples.py` | the bundled example logs offered on the landing page |
| `knowledge.py` | loads `v2/knowledge/*.toml`, re-reading a file when its mtime changes |

Everything the backend derives carries the line numbers it came from, so the frontend can
highlight the evidence for a claim instead of asserting it.

## `v2/knowledge` - the editable knowledge base

Plain TOML: block explanations, table and column texts, subsolver descriptions and roles,
constraint kinds, solver messages, parameter advice and warnings, insight thresholds and
texts, metric thresholds, example descriptions. A CP-SAT expert can change any wording or tune
any threshold without touching Python; `v2/knowledge/README.md` maps each kind of text to its
file and `python -m app.knowledge` validates the result.

This is also why the frontend needs no change for a new insight: it renders whatever
`analysis.insights` contains.

## `v2/frontend` - the UI

React + Vite + Plotly. `AnalysisPanel` (Overview tiles, insights, progress plot, parameters,
subsolvers, one card per log block) on the left, `LogView` with the raw log on the right, a
`Splitter` between them, and a line index that links the two. Block cards are specialised per
section (`blocks/ModelBlock`, `PresolveBlock`, `SearchBlock`, `ResponseBlock`, `TableBlock`,
...); `Md.tsx` renders the Markdown that comes from the knowledge base. Lines the parser could
not use are marked in both panes (`k-unparsed`: dashed border, tinted background), so a broken
log is recognisable as such at a glance instead of looking like a complete analysis.

## Test data

* `example_logs/` - the 10 logs offered in the UI, chosen for diversity of log shapes;
  `example_logs/archive/` holds retired ones (older OR-Tools formats, redundant variants) that
  the test suites still parse.
* `v2/corpus/benchmark_logs.tar.xz` - 295 real logs from the `benchmarks/` harness, the
  regression base for both parser and analysis. See `v2/corpus/README.md`.

## The legacy app

The original Streamlit implementation (`app.py`, `_app/`, `cpsat_log_parser/`) lived in the
repository root until it was moved to the `legacy` branch. It shares no code with `v2/` and is
feature-frozen; see [deployment.md](deployment.md#legacy-streamlit-app) for what still serves
it.

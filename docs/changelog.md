# Changelog

Notable changes, newest first. Dates are the day the work landed on `main`.

## v2 stack (`v2/`)

* **2026-09-06** - Committed the benchmark log corpus (295 real logs, compressed in
  `v2/corpus/`) and made it a test suite for both the parser and the analysis; trimmed the
  landing-page examples to ten logs chosen for diversity and moved the rest to
  `example_logs/archive/`.
* **2026-09-06** - Audited the whole knowledge base against the corpus and corrected six wrong
  claims (most importantly: the `CpSolverResponse` counters belong to the worker that finished
  first, not to the first full worker); added the *Presolve fixed the objective* insight.
* **2026-09-06** - Added the `benchmarks/` harness that collects logs by solving public
  instances (21 problem classes plus 30 MiniZinc Challenge families).
* **2026-09-05/06** - v2 rewrite: `cpsatlog` parser library with line-anchored pydantic
  models, FastAPI backend with derived analysis and insights, React/Vite frontend with the
  two-pane linked view, and the editable TOML knowledge base.

## Streamlit app (repository root)

* **2024-10-31** - Added a log history to quickly switch back to previous logs.
* **2024-10-31** - Fixed parsing when the model was solved in presolve.
* **2024-09-05** - Improved the parsing of the parameters.
* **2024-09-05** - No longer warn if the status is `OPTIMAL` but there is a gap: CP-SAT
  considers everything optimal within a specified tolerance, unlike other solvers.

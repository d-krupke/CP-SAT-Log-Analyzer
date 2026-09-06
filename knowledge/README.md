# Editing the CP-SAT knowledge of the analyzer

Almost everything the analyzer *says* about a log lives in this directory as
plain [TOML](https://toml.io) files. You do not need to know Python, TypeScript
or React to change a text, add a subsolver, tune a threshold or explain a new
table column. The code only decides *where* a text is shown; the files here
decide *what* it says.

The exception is the colored insight boxes of the Overview. Those fire on a
condition rather than on a section of the log, so each one is a small Python
class in `backend/app/insights/triggers/` that holds its own threshold and
wording - see "Adding things" below.

## Which file do I edit?

| I want to change ... | File | Key |
| --- | --- | --- |
| the explanation on top of a log-section card (Solver, Initial model, Presolve, Search progress, Response, ...) | `blocks.toml` | `[blocks]`, key = section kind |
| the intro of the Search progress plot, the Parameters card, the Subsolver contributions card or the Solution hint card | `blocks.toml` | `[cards]` |
| a statistics table (`Search stats`, `Lp stats`, `LNS stats`, ...) or one of its columns | `tables.toml` | `[tables.<table_id>]`, `[tables.<table_id>.columns]` |
| a field of the `CpSolverResponse summary:` | `response_fields.toml` | `[response_fields]` |
| what a worker/subsolver does (`core`, `max_lp`, `rins`, ...), its role, the group descriptions | `subsolvers.toml` | `[subsolvers.<name>]`, `[roles]`, `[categories]`, `[[patterns]]` |
| the one-liner for a constraint kind (`kNoOverlap2D`, ...) and whether it counts as simple/encoded/global | `constraints.toml` | `[constraints.<kind>]`, `[complexity]` |
| the domain-size levels (Boolean/small/medium/large) and texts of the model cards | `model.toml` | `[domain_size]`, `[[domain_size.level]]` |
| the explanation of a solver message (`Problem closed by presolve.`, every `hint_*` verdict, ...) | `messages.toml` | `[messages]` |
| advice for an overridden parameter, which parameters get a warning and the warning text | `parameters.toml` | `[advice]`, `safe`, `[[warning]]` |
| when a tile in the Overview turns yellow/red and its hint | `metrics.toml` | one section per tile |
| the description of an example log offered on the landing page | `examples.toml` | `[examples]` |
| the description of a retired example log (`example_logs/archive/`, test material only) | `examples.toml` | `[archived]` |

The official documentation of each parameter (shown under "Documentation from
sat_parameters.proto") is *not* here: it is generated from OR-Tools into
`backend/app/data/sat_parameters.json` by `tools/extract_sat_parameters.py`.

## Writing texts

- Texts are Markdown: `**bold**`, `` `code` ``, `*italic*`, lists with `- `.
- Short texts go in single quotes on one line: `n = 'Number of runs.'`
- Longer texts use three single quotes and may span lines; line breaks inside a
  paragraph are ignored when rendered, an empty line starts a new paragraph:

  ```toml
  [subsolvers.core]
  role = 'exact'
  summary = 'Core-guided optimization: lifts the lower bound through unsat cores.'
  details = '''
  `optimize_with_core = true`, no LP. Assumes every objective term at its best
  value and asks the SAT core for a solution ...'''
  ```

- Inside `'''...'''` you cannot use three single quotes; everything else
  (backslashes, quotes, braces) is taken literally - there are no placeholders.
- Keys with unusual characters must be quoted: `"DUAL_F." = '...'`,
  `"Cuts/Call" = '...'`.

## Adding things

- **A new subsolver name** appears in a log: add `[subsolvers.<name>]` with
  `role`, `summary` and `details`. Names of the form `<known>_something`
  (e.g. `rins_lns_default`) automatically fall back to `<known>`, and the
  `[[patterns]]` at the end of `subsolvers.toml` catch whole families.
- **A new table or column** in a newer OR-Tools version: add
  `[tables.<table_id>]` where `table_id` is the table title in lower case with
  spaces replaced by underscores (`Lp stats` -> `lp_stats`). Column keys must
  match the printed header exactly. Unknown tables still render, just without
  explanation.
- **A new parameter warning**: append a `[[warning]]` rule to
  `parameters.toml`. Rules are checked top to bottom, the first match wins,
  and parameters listed in `safe` never warn.
- **A new insight box** (the colored observations in the Overview) is *not*
  here: it is a small Python class in `backend/app/insights/triggers/`,
  because deciding *when* to say something needs more than a threshold. The
  class holds its own threshold, level, title and text right next to the check;
  `backend/app/insights/base.py` shows the shape and the house rules for the
  wording.

## Checking your edit

From `backend`:

```sh
uv run python -m app.knowledge     # "OK: all knowledge files ... load." or the exact error
uv run pytest                      # the full backend test suite also covers the files
```

A running development server picks up saved files on the next request; no
restart needed. The Docker image copies this directory at build time, so
rebuild the image to ship a change.

## Where the knowledge comes from

The explanations follow the CP-SAT primer chapter *How CP-SAT Reasons: The
Search Core* (`search_core.md`) and were cross-checked against the OR-Tools
sources, mainly `ortools/sat/cp_model_search.cc` (portfolio definitions),
`cp_model_solver.cc` (LNS and local-search workers), `cp_model_solver_logging.cc`,
`stat_tables.cc` and `synchronization.cc`. When you change a claim, please keep it
consistent with those sources and mention the OR-Tools version it refers to if it
is version specific.

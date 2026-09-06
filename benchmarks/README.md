# CP-SAT log benchmarks

Collects CP-SAT search logs from diverse, well-known benchmark instances as
base data for the log analyzer (what do real logs look like, which patterns
occur). Created 2026-09-06. Instances (`data/`), logs (`logs/`) and the
MiniZinc bundle (`tools/`) are kept locally and are git-ignored.

```sh
uv sync                                   # Python 3.12 + ortools
uv run python run.py list                 # 20 problem classes
uv run python run.py download             # fetch all instance files (~40 MB)
uv run python run.py solve jobshop --limit 60 --workers 8 --max-instances 5
uv run python run.py solve                # no names = every problem class
./collect_all.sh                          # the full corpus (five batches, hours)
```

## Layout

| Path | What |
| --- | --- |
| `bench/base.py` | `Problem`/`Instance` contract plus the idempotent `fetch()` downloader |
| `bench/problems/<name>.py` | one problem class each, auto-registered through its `PROBLEM` |
| `bench/runner.py` | solves one instance and writes the log + metadata |
| `run.py` | CLI: `list`, `download`, `solve` |
| `mzn_run.py` | MiniZinc Challenge families through the bundled MiniZinc + `cp-sat` backend |
| `validate_logs.py` | parses every collected log with the v2 `cpsatlog` parser and reports gaps |
| `collect_all.sh` | the batches that produce the corpus (worker counts, parameter variants) |

## Logs

`logs/<problem>/<instance>__w<workers>_t<limit>[_<tag>].txt` with a sibling
`.json` (problem, instance, source, parameters, status, objective, bound, wall
time, model size). Existing logs are skipped, so every command is resumable;
`--force` overwrites. `--tag` keeps parameter variants of the same instance
apart (`--param linearization_level=0 --tag nolp`). `--max-instances N` picks N
instances spread over the file sizes, not the N smallest.

On a loaded machine run the batches one problem at a time in the foreground:
`collect_all.sh` in the background was twice killed by the system's low-memory
guard while the machine sat in ~21 GB of swap, even though the solves themselves
stayed small. Every command is resumable, so a killed run loses nothing.

## Diversity of the corpus

- 20 problem classes: scheduling (job shop, flexible job shop, RCPSP), packing
  (1D bin packing, 2D bin packing, strip packing), routing (TSP, CVRP), graphs
  (colouring, max clique, dominating set), OR-Library (set covering,
  multi-knapsack, GAP, QAP) and pure satisfaction puzzles (sudoku, n-queens,
  Langford, Golomb ruler, Costas arrays).
- 30 MiniZinc Challenge families, which show what compiler-generated models look
  like (`mznfile…` model names, FlatZinc search strategies, many Booleans).
- Worker counts 1 / 8 / 16 (single `main` worker vs. portfolio vs. large
  portfolio) and parameter variants (`linearization_level=0`,
  `cp_model_presolve=false`, `use_lns_only`, `interleave_search`,
  `enumerate_all_solutions`).

## MiniZinc

The bundle in `tools/` (MiniZinc 2.10.1 with the OR-Tools 9.15 `cp-sat`
backend) and a sparse checkout of `MiniZinc/minizinc-benchmarks` in
`data/minizinc/repo` are the inputs. MiniZinc prints the CP-SAT log as
FlatZinc comments; `mzn_run.py` strips the `%% ` prefix and drops the
`%%%mzn-stat` lines, so the stored files are plain CP-SAT logs.

```sh
uv run python mzn_run.py list
uv run python mzn_run.py solve rcpsp steelmillslab --limit 60 --max-instances 2
```

## Checking the corpus against the parser

```sh
uv run --project ../v2/cpsatlog python validate_logs.py
```

Prints per problem how many logs parsed, which top-level sections are missing
and which chunks the parser left in `log.unparsed` — that list is the to-do
list for the parser and the knowledge base.

## Audit of the knowledge base against the corpus (2026-09-06)

Every quantitative claim in `v2/knowledge/` that the 295 logs can test was checked;
each one that failed was traced to the OR-Tools sources before the text was changed.

Confirmed by the logs:

- Full workers per `num_workers`: 1 -> `main` only, 8 -> 6, 16 -> 11 (optimisation).
  Satisfaction at 16 gives 13, six of them `shared_tree`, which is exactly the automatic
  rule `(num_workers - 8) * 3 / 4 > 4`.
- `fixed` is in the roster if and only if the model has a decision strategy or scheduling
  constraints (250/250 portfolio runs).
- Global `search_branching = FIXED_SEARCH` without either drops `default_lp`, `no_lp` and
  `max_lp` from the portfolio (two MiniZinc logs show it).
- `feasibility_pump` disappears with `linearization_level = 0`; `feasibility_pump` and
  `rins/rens` disappear with `interleave_search`, with 1 worker and with `use_lns_only`.
- Automatic interleave batch size is `num_workers * 3` (24 at 8 workers).
- `ls` needs an objective; one `ls` at 8 workers, `ls` + `ls_lin` at 16.
- `lb_relax_lns` only appears from 16 workers on.
- `no_lp` and `core` never have an `Lp stats` row.
- `usertime` equals `walltime` in all 295 logs.
- All twelve insight rules fire on real logs and no threshold is degenerate.

Corrected because the logs contradicted the text:

- The response counters (`conflicts`, `branches`, ...) are **not** those of the first full
  worker. Each worker hands its statistics over when it is freed and only the first of those
  is merged, so they belong to the worker that finished first: `fs_random_no_lp` in 29 of the
  85 unambiguous logs, `default_lp` in 11.
- `Search stats` also has rows for the `fs_*` first-solution workers.
- `Conflicts` can exceed `Branches` (two logs), so the ratio is not bounded by 1.
- Full workers run once only without `interleave_search`; with it `n` counts batches.
- `core` is dropped when the objective has at most one variable, which includes objectives
  that presolve removes entirely (`( in objective)`); the other objective-based workers and
  all LNS neighbourhoods go with it.
- The portfolio line repeats a strategy (`default_lp(2)`, `fj(2)`, `shared_tree(6)`) when the
  roster is shorter than the worker budget.

`Setting number of shared tree workers to N` is now parsed into the solver header instead of
being kept as a free-form line.

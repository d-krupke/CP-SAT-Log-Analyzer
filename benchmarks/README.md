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

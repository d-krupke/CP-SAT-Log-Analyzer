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
| `validate_logs.py` | parses every collected log with the `cpsat_logutils` parser and reports gaps |
| `collect_all.sh` | the batches that produce the corpus (worker counts, parameter variants) |
| `make_hint_example.py` | generates the solution-hint example pair (see below); not part of the corpus |

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
  (coloring, max clique, dominating set), OR-Library (set covering,
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
uv run python validate_logs.py
```

Prints per problem how many logs parsed, which top-level sections are missing
and which chunks the parser left in `log.unparsed` — that list is the to-do
list for the parser and the knowledge base.

## Committed archive and the frontend examples (2026-09-06)

The logs are git-ignored, but they are also the best regression input the project has, so
they are shipped compressed:

```sh
uv run python pack_corpus.py       # -> ../corpus/benchmark_logs.tar.xz (~0.9 MB, 295 logs)
```

Re-run it after every batch and commit the archive; it is byte-reproducible, so an unchanged
corpus produces no diff. The archive carries the `.txt` logs plus a normalized `index.json`
(problem, instance, parameters, version, status, objective, bound, walltime, model size,
source URL) instead of the raw sidecars, because the MiniZinc sidecars embed the full
solution output of third-party models. The instances themselves stay local - they may be
copyrighted. Two test suites read the archive: `backend/tests/test_corpus.py` here (`analyze()` works,
insight texts render, every worker and every parameter is documented) and, from a copy of the
archive in [cpsat-logutils](https://github.com/d-krupke/cpsat-logutils), its
`tests/test_corpus.py` (every log parses, nothing unparsed, parsed values match `index.json`).
See `corpus/README.md`.

Corpus logs also became the frontend's examples. The landing page offered ten `915_*`
logs, selected for diversity rather than coverage of every parameter: one small introductory
run, a job-shop instance on 1 and on 8 workers, a 16-worker satisfaction model with
shared-tree search, `use_lns_only` (no exact worker at all), an objective that presolve pins
to a constant, a presolve blow-up from 1,275 to 3 million variables with no search at all, a
proven infeasibility, a satisfaction model that stays UNKNOWN, and a FlatZinc model from
MiniZinc - so each entry differs in problem type, status, portfolio shape, presolve effect or
constraint family. Everything retired from that list, including all the pre-9.15 logs, moved
to `example_logs/archive/`: the API does not serve it, but both test suites still parse it
(the only coverage of the 9.3 ... 9.10 log formats). Curated texts for both groups live in
`knowledge/examples.toml` (`[examples]` and `[archived]`); a test fails if an offered
example has no description or if an archived one shows up on the landing page.

## Generated examples: the solution-hint pair (2026-09-06)

Some behavior does not show up in a corpus that solves every instance once. Nothing in the 295
logs is a run with a *useful* solution hint - the 11 logs whose output mentions a complete and
feasible hint were given no hint at all (CP-SAT prints that sentence when presolve has fixed
every variable). So `make_hint_example.py` produces the missing case on purpose:

```sh
uv run python make_hint_example.py     # writes both logs into example_logs/
```

It builds one random 15x15 job shop (fixed seed, 10 s, 8 workers), solves it plain, then builds
the *same* model a second time and hints it with the first run's solution - a fresh model,
because re-solving the solved one would reuse its solution pool. The result is a pair that
differs in exactly one thing: `915_jobshop_no_hint` climbs from 1390 to 1146 over 109 improving
solutions, while `915_jobshop_hinted` starts at 1146 after 0.01 s with a single
`#1 ... complete_hint` event and reaches the same bound. Both are offered on the landing page.

## Audit of the knowledge base against the corpus (2026-09-06)

Every quantitative claim in `knowledge/` that the 295 logs can test was checked;
each one that failed was traced to the OR-Tools sources before the text was changed.

Confirmed by the logs:

- Full workers per `num_workers`: 1 -> `main` only, 8 -> 6, 16 -> 11 (optimization).
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
  all LNS neighborhoods go with it.
- The portfolio line repeats a strategy (`default_lp(2)`, `fj(2)`, `shared_tree(6)`) when the
  roster is shorter than the worker budget.

`Setting number of shared tree workers to N` is now parsed into the solver header instead of
being kept as a free-form line.

The audit also produced one new insight, `objective_removed_by_presolve`: six logs have an
initial objective and a presolved line printing the empty form `( in objective)`, which silently
removes the objective-based workers and every LNS neighborhood from the portfolio. The rule
fires on exactly those six logs and on none of the other 289.

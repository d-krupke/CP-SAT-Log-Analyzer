# Benchmark log corpus (regression test data)

`benchmark_logs.tar.xz` holds **295 real CP-SAT logs** (OR-Tools 9.15, ~16 MB uncompressed)
collected by the `benchmarks/` harness in September 2026: 21 problem classes solved from
public instance libraries (JSPLIB, PSPLIB, BPPLIB/2DPackLib, DIMACS, TSPLIB/CVRPLIB,
OR-Library, QAPLIB, CSPLib puzzles) plus 30 MiniZinc Challenge families driven through
MiniZinc's `cp-sat` backend. Each class was run with several worker counts, time limits and
parameter variants (`num_workers=1/8/16`, `interleave_search`, `use_lns_only`,
`cp_model_presolve=false`, `linearization_level=0`, `enumerate_all_solutions`), so the archive
covers the log shapes the parser and the analyzer have to survive.

## Why it is committed and the instances are not

The logs are plain solver output and small once compressed, so they can live in the repository
and be used as test data. The **instances** behind them may be copyrighted and stay local
(`benchmarks/data/` is git-ignored), and so do the raw per-run JSON sidecars: the MiniZinc ones
embed the full solution the solver printed for a third-party model.

## Layout

```
index.json                 metadata per log, keyed by the path below
logs/<problem>/<run>.txt    e.g. logs/jobshop/ta61__w8_t60.txt
logs/minizinc/<family>/<run>.txt
```

`index.json` entries carry only what tests need: `problem`, `instance`, `origin`
(`native` | `minizinc`), `parameters`, and for native runs `ortools_version`, `status`,
`objective`, `best_bound`, `wall_time`, `num_variables`, `num_constraints`, `source` (the URL
the instance came from). Three early runs predate the version field, and MiniZinc runs have no
response fields, so treat every key as optional.

## Regenerating

```sh
uv run python benchmarks/pack_corpus.py      # needs the local benchmarks/logs/
```

The archive is byte-reproducible (fixed member order, owner and mtime), so re-packing an
unchanged corpus produces no diff.

## Who reads it

* `v2/cpsatlog/tests/test_corpus.py` - every log parses, leaves nothing in `log.unparsed`, and
  the parsed response matches `index.json`.
* `v2/backend/tests/test_corpus.py` - `analyze()` succeeds on every log and every insight text
  renders.

Both suites skip themselves if the archive is missing, so a shallow checkout still runs.

# CP-SAT Log Analyzer

CP-SAT's search log is dense, long, and full of information that only makes sense if you know
the solver's internals. This tool turns it into something you can read: parsed, explained,
plotted, and annotated with what the numbers actually mean for *your* model.

Paste a log, upload a file, or click one of the bundled examples. Nothing is stored - your log
is parsed and thrown away.

_This project is not affiliated with Google._

## What it does

The features below describe the stack in [`v2/`](v2/README.md), which you run with one
`docker compose up`.

**Explains every section of the log.** Solver header, initial and presolved model, presolve
passes, search events, statistics tables, response summary - each gets a text that says what it
is and what to look for. Tables and their columns, constraint kinds (`kNoOverlap2D`,
`kAllDiff`, ...), solver messages and every response field are documented too.

**Points out what matters.** An Overview card scores the run - OR-Tools version, worker count,
final gap, presolve share of the wall time, solutions and bound improvements, and whether a
solution hint was given and used - and colors a
tile when something deserves attention. On top of that, two dozen insight triggers look for
specific situations and say what they imply, for example:

* *Not proven optimal* - and whether solutions or bounds stalled first;
* *Hint used as the first solution* - or why your hint was rejected;
* *Presolve expanded the model* - a global constraint was unrolled into thousands of Booleans;
* *Presolve fixed the objective* - the portfolio then loses every objective worker and all LNS;
* *Log ends before the response summary* - so everything below it is partial;
* *LNS neighborhoods closed quickly*, *solutions stalled early*, *solved by presolve*, ...

**Says what became of your hint.** Whether a solution hint reached the solver, whether it was
complete and feasible, and whether CP-SAT actually started from it (the `complete_hint`
solution) - including the trap that CP-SAT prints "The solution hint is complete and is
feasible." for runs that were given no hint at all.

**Plots the progress.** Incumbent objective and proven bound over time, interactive, and every
point links back to the log line that produced it.

**Attributes the work.** Which subsolver found the solutions, which raised the bound, and what
each of the ~20 workers in CP-SAT's portfolio (`default_lp`, `core`, `fs_random_no_lp`,
`graph_arc_lns`, `shared_tree`, ...) is actually for.

**Reviews your parameters.** Every overridden parameter is shown with its official
documentation, practical advice, and a warning when it quietly disables part of the portfolio -
`interleave_search`, `use_lns_only`, `linearization_level`, `FIXED_SEARCH` and friends have
consequences that the log alone does not spell out.

**Copes with broken logs.** A run that was killed, a log clipped by a terminal, one prefixed by
a logging framework, your own prints mixed in, or the wrong file entirely: nothing crashes, the
parts that could not be read are marked in the raw log and listed, and the analysis says up
front that it is looking at an incomplete log.

**Keeps the evidence.** Every parsed value knows the line it came from, so the analysis and the
raw log sit side by side, linked in both directions - no claim without the line that supports
it.

**Speaks CP-SAT 9.3 to 9.15**, including the older log formats, and is checked against 295 real
logs from public instance libraries on every test run.

## Try it

```sh
git clone https://github.com/d-krupke/CP-SAT-Log-Analyzer.git
cd CP-SAT-Log-Analyzer/v2
docker compose up --build
# open http://localhost:8080
```

The earlier Streamlit implementation - the one behind
<https://cpsat-log-analyzer.streamlit.app/> - is no longer part of this branch; it lives on the
`legacy` branch and is feature-frozen.

Deploying it for others, configuration, sizing and operations:
[docs/deployment.md](docs/deployment.md).

## Documentation

| Read this | For |
| --- | --- |
| [docs/deployment.md](docs/deployment.md) | running it for other people |
| [docs/development.md](docs/development.md) | local setup, tests, editing the explanations |
| [docs/architecture.md](docs/architecture.md) | how the parser, backend, knowledge base and UI fit together |
| [docs/README.md](docs/README.md) | index, including the per-component READMEs |

Everything lives in [`v2/`](v2/README.md): the `cpsatlog` parser library, the FastAPI backend,
the React frontend, the TOML knowledge base and the log corpus the tests run against.

## Contributing

Issues and pull requests are welcome. Two things are easy to contribute without touching much
code:

* **Explanations.** All CP-SAT knowledge is plain TOML in
  [`v2/knowledge/`](v2/knowledge/README.md) - texts, parameter advice, subsolver descriptions,
  table columns. Correcting or sharpening a text needs no Python.
* **Insights.** A new colored box is one small class in
  [`v2/backend/app/insights/triggers/`](v2/backend/app/insights/): it gets the parsed log and
  either stays quiet or writes its sentence. `base.py` shows the shape.
* **Logs.** A log the parser mishandles, or one that shows an interesting pathology, is a
  useful issue by itself.

Before opening a pull request, run the suites listed in
[docs/development.md](docs/development.md).

## Authors

Developed by [Dominik Krupke](https://github.com/d-krupke/), Algorithms Group, TU
Braunschweig. There is no funding for this project; it is mainly developed in spare time. If
you want to support it, contribute or get in touch.

## Related projects

1. [OR-Tools](https://github.com/google/or-tools/) - Google's Operations Research tools,
   containing the CP-SAT solver this project was written for.
2. [CP-SAT Primer](https://github.com/d-krupke/cpsat-primer) - a primer on constraint
   programming with CP-SAT; this analyzer complements it.
3. [gurobi-logtools](https://github.com/Gurobi/gurobi-logtools) - Gurobi's log analyzer, the
   original inspiration.

## License

MIT, see [LICENSE](LICENSE).

# cpsatlog

Parse [CP-SAT](https://developers.google.com/optimization/cp/cp_solver) (OR-Tools)
solver logs into **line-anchored, JSON-serialisable pydantic models**.

```python
from cpsatlog import parse_log

log = parse_log(open("solver.log").read())

log.solver.version.value  # "9.15.6755"
log.solver.parameters.value  # {"max_time_in_seconds": 5, "num_workers": 8, ...}
log.response.status.value  # "OPTIMAL"
log.response.status.line  # 346  <- every value knows its line
log.search.events[0].objective  # first solution value
log.stats.search_stats.row("core").values["Conflicts"]
log.block_at(line=42)  # -> BlockRef(kind="presolve", span=..., path="/presolve")
log.model_dump_json(indent=2)  # plain JSON
```

Sections that do not occur in a log are simply `None`.

## Why line anchors?

Log analysers want to show the raw text next to the parsed data. Every scalar
is a `Loc[T]` (`value` + `line`), table rows carry their `line`, every section
has a `span`, and `CpSatLog.blocks` is an ordered index (`kind`, `span`, JSON
pointer `path`) that maps any line back to the parsed section.

## Supported versions

Tested against example logs from OR-Tools 9.3 to 9.15. Known format traps
(older `[Name] ... time=` presolve lines, `Solutions found per subsolver:` lists,
progress lines inside the presolve block, `LRAT_status`, renamed table columns)
are handled; unknown sections are kept verbatim in `log.unparsed` and never
raise.

## Extending

* `splitter.py` cuts text into chunks; add forced cut points there when a new
  version glues sections together.
* `parsers/` holds one `BlockParser` per section; register new ones in
  `parsers/__init__.py` (first match wins).
* `parsers/tables.py::TABLE_IDS` maps table titles to stable ids; add a line for
  a new table and give it a field in `schema/tables.py::FinalStats`.
* `assemble.py` places blocks into the root model and merges multi-chunk sections.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ty check
```

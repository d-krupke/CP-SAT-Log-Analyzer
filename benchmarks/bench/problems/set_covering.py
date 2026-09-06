"""Set covering (SCP) from Beasley's OR-Library.

What: one problem class of the CP-SAT log benchmark harness -- the weighted and
unicost set covering problems ``scp*`` of the OR-Library.  Created 2026-09-06 to
give the log analyzer real logs of pure 0/1 covering models: huge but very
shallow models (only clauses plus one linear objective), where CP-SAT's LP
relaxation and its clause-based presolve dominate the log.

Source: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/scpinfo.html
Files:  https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/scp41.txt etc.

Format (whitespace separated, line breaks are irrelevant)::

    m n                     number of rows, number of columns
    c_1 ... c_n             cost of every column
    for each of the m rows:
        k                   number of columns that cover this row
        j_1 ... j_k         the covering columns, 1-based

The ``scpcyc*`` and ``scpclr*`` families are unicost (all costs are 1) and are
combinatorially much harder than their file size suggests.

Model: one Boolean per column, one ``AddBoolOr`` per row, minimise the cost sum.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files"

# Ordered easy -> hard.  Interleaves the weighted Beasley families (4/5/6, a-d,
# nre-nrh) with the unicost cyc/clr families, which are small but much harder.
FILES: tuple[str, ...] = (
    "scpcyc06",
    "scp41",
    "scp42",
    "scp45",
    "scpcyc07",
    "scp51",
    "scp52",
    "scp61",
    "scp62",
    "scpclr10",
    "scpa1",
    "scpa2",
    "scpcyc08",
    "scpb1",
    "scpb2",
    "scpclr11",
    "scpc1",
    "scpc2",
    "scpcyc09",
    "scpd1",
    "scpd2",
    "scpclr12",
    "scpnre1",
    "scpnre2",
    "scpcyc10",
    "scpnrf1",
    "scpnrf2",
    "scpclr13",
    "scpnrg1",
    "scpnrg2",
    "scpcyc11",
    "scpnrh1",
    "scpnrh2",
)


@dataclass(frozen=True)
class ScpData:
    """A parsed set covering instance."""

    num_rows: int
    num_cols: int
    costs: list[int]
    rows: list[list[int]]  # per row the 0-based indices of the covering columns

    @property
    def nnz(self) -> int:
        return sum(len(r) for r in self.rows)

    @property
    def unicost(self) -> bool:
        return all(c == self.costs[0] for c in self.costs)


def parse_scp(path: Path) -> ScpData:
    """Parse the OR-Library SCP format; tolerant of arbitrary line wrapping."""
    tokens = path.read_text().split()
    pos = 0

    def take() -> int:
        nonlocal pos
        value = int(float(tokens[pos]))
        pos += 1
        return value

    num_rows, num_cols = take(), take()
    costs = [take() for _ in range(num_cols)]
    rows: list[list[int]] = []
    for _ in range(num_rows):
        count = take()
        rows.append([take() - 1 for _ in range(count)])
    if pos != len(tokens):
        raise ValueError(f"{path.name}: {len(tokens) - pos} trailing tokens")
    return ScpData(num_rows, num_cols, costs, rows)


def download(data_dir: Path) -> None:
    for name in FILES:
        fetch(f"{BASE_URL}/{name}.txt", data_dir / f"{name}.txt")


def instances(data_dir: Path) -> list[Instance]:
    out: list[Instance] = []
    for name in FILES:
        path = data_dir / f"{name}.txt"
        if not path.exists():
            continue
        # Read only the header for the size hints; the body is parsed in build().
        head = path.read_text()[:64].split()
        rows, cols = int(head[0]), int(head[1])
        out.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "rows": rows,
                    "columns": cols,
                    "family": _family(name),
                    "unicost": name.startswith(("scpcyc", "scpclr")),
                },
            )
        )
    return out


def _family(name: str) -> str:
    body = name.removeprefix("scp")
    return "".join(ch for ch in body if not ch.isdigit()) or "beasley"


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    data = parse_scp(instance.path)
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{j}") for j in range(data.num_cols)]
    for i, cols in enumerate(data.rows):
        if not cols:
            raise ValueError(f"{instance.name}: row {i} is coverable by no column")
        model.add_bool_or([x[j] for j in cols])
    model.minimize(cp_model.LinearExpr.weighted_sum(x, data.costs))
    return model


PROBLEM = Problem(
    name="set_covering",
    description="Weighted and unicost set covering (OR-Library scp*)",
    download=download,
    instances=instances,
    build=build,
    source="https://people.brunel.ac.uk/~mastjjb/jeb/orlib/scpinfo.html",
)

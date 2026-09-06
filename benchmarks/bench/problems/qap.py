"""Quadratic assignment problem (QAP) from QAPLIB.

What: one problem class of the CP-SAT log benchmark harness.  Created
2026-09-06 because the QAP is the classic "CP-SAT struggles to close the gap"
model: an alldifferent/assignment core with a quadratic objective, so the logs
show a good primal solution within seconds and a dual bound that barely moves.
The module deliberately builds *two* very different encodings so the collected
logs cover both shapes (a huge Boolean-product model vs. a tiny element model).

Source: QAPLIB, https://coral.ise.lehigh.edu/data-sets/qaplib/
Files:  the coral.ise.lehigh.edu downloads are behind a 403, so the instance
        files are taken from the QAPLIB copy shipped with the CRAN package
        ``qap``: https://github.com/mhahsler/qap/tree/master/inst/qaplib

Format (whitespace separated, line wrapping is irrelevant)::

    n
    F   (n x n flow matrix)
    D   (n x n distance matrix)

Objective: minimize ``sum_{i != j} F[i][j] * D[p(i)][p(j)]`` over permutations p.
All instances used here have symmetric F and D, which lets the objective be
written over unordered plant pairs ``i < j`` with ``G[i][j] = F[i][j] + F[j][i]``.

Model, two variants selected by size:

* ``n <= 20`` -- assignment Booleans ``x[i][k]`` with ExactlyOne per row and
  column, plus a Boolean product ``y = x[i][k] & x[j][l]`` for every pair
  ``i < j`` with non-zero flow and every ordered location pair with non-zero
  distance.  Stays below ~150k Booleans thanks to the sparsity filters.
* ``n > 20`` -- an integer permutation ``p[i]`` with AddAllDifferent and one
  ``AddElement`` per flow pair over the flattened distance matrix, indexed by
  ``p[i] * n + p[j]``.  A few thousand variables even for ``wil50``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ortools.sat.python import cp_model

from ..base import Instance, Problem, fetch

BASE_URL = "https://raw.githubusercontent.com/mhahsler/qap/master/inst/qaplib"

# Ordered easy -> hard (by n, then by flow density).  Everything up to and
# including tai20a uses the Boolean-product model, the last three the element
# model.  esc16f is intentionally absent: its flow matrix is all zero.
FILES: tuple[str, ...] = (
    "tai10a",
    "chr12a",
    "scr12",
    "nug12",
    "had12",
    "rou12",
    "tai12a",
    "had14",
    "nug14",
    "chr15a",
    "scr15",
    "nug15",
    "rou15",
    "tai15a",
    "esc16j",
    "esc16i",
    "esc16a",
    "esc16b",
    "nug16a",
    "nug18",
    "els19",
    "had20",
    "nug20",
    "tai20a",
    "kra30a",
    "ste36a",
    "wil50",
)

# Above this size the Boolean-product model would explode; use AddElement.
PRODUCT_MAX_N = 20


@dataclass(frozen=True)
class QapData:
    """A parsed QAPLIB instance: flow and distance matrix of equal size."""

    n: int
    flow: list[list[int]]
    dist: list[list[int]]

    def pairs(self) -> list[tuple[int, int, int]]:
        """Unordered plant pairs ``(i, j, G[i][j])`` with non-zero total flow."""
        out = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                g = self.flow[i][j] + self.flow[j][i]
                if g:
                    out.append((i, j, g))
        return out


def parse_qap(path: Path) -> QapData:
    tokens = path.read_text().split()
    n = int(tokens[0])
    values = [int(float(t)) for t in tokens[1:]]
    if len(values) != 2 * n * n:
        raise ValueError(
            f"{path.name}: expected {2 * n * n} matrix entries, got {len(values)}"
        )
    flow = [values[i * n : (i + 1) * n] for i in range(n)]
    off = n * n
    dist = [values[off + i * n : off + (i + 1) * n] for i in range(n)]
    return QapData(n, flow, dist)


def download(data_dir: Path) -> None:
    for name in FILES:
        fetch(f"{BASE_URL}/{name}.dat", data_dir / f"{name}.dat")


def instances(data_dir: Path) -> list[Instance]:
    out: list[Instance] = []
    for name in FILES:
        path = data_dir / f"{name}.dat"
        if not path.exists():
            continue
        n = int(path.read_text()[:32].split()[0])
        out.append(
            Instance(
                name=name,
                path=path,
                meta={
                    "n": n,
                    "formulation": "products" if n <= PRODUCT_MAX_N else "element",
                    "family": "".join(ch for ch in name if not ch.isdigit()),
                },
            )
        )
    return out


def build(instance: Instance) -> cp_model.CpModel:
    assert instance.path is not None
    data = parse_qap(instance.path)
    if data.n <= PRODUCT_MAX_N:
        return _build_products(data)
    return _build_element(data)


def _build_products(data: QapData) -> cp_model.CpModel:
    """Assignment Booleans plus one product variable per (flow pair, location pair)."""
    n, dist = data.n, data.dist
    model = cp_model.CpModel()
    x = [[model.new_bool_var(f"x_{i}_{k}") for k in range(n)] for i in range(n)]
    for i in range(n):
        model.add_exactly_one(x[i])
    for k in range(n):
        model.add_exactly_one(x[i][k] for i in range(n))

    # Non-zero distances only; the diagonal is always skipped (k == l is
    # impossible for i != j once the assignment constraints hold).
    loc_pairs = [
        (k, l, dist[k][l]) for k in range(n) for l in range(n) if k != l and dist[k][l]
    ]

    terms: list[cp_model.LinearExpr] = []
    coeffs: list[int] = []
    for i, j, g in data.pairs():
        for k, ell, d in loc_pairs:
            y = model.new_bool_var(f"y_{i}_{k}_{j}_{ell}")
            # y <=> x[i][k] and x[j][l]
            model.add_implication(y, x[i][k])
            model.add_implication(y, x[j][ell])
            model.add_bool_or([~x[i][k], ~x[j][ell], y])
            terms.append(y)
            coeffs.append(g * d)
    model.minimize(cp_model.LinearExpr.weighted_sum(terms, coeffs))
    return model


def _build_element(data: QapData) -> cp_model.CpModel:
    """Integer permutation with a 2D AddElement lookup into the distance matrix."""
    n, dist = data.n, data.dist
    model = cp_model.CpModel()
    p = [model.new_int_var(0, n - 1, f"p_{i}") for i in range(n)]
    model.add_all_different(p)
    # Symmetry breaking would cut off optimal solutions here, so none is added.

    flat = [dist[k][ell] for k in range(n) for ell in range(n)]
    lo, hi = min(flat), max(flat)
    terms: list[cp_model.LinearExpr] = []
    coeffs: list[int] = []
    for i, j, g in data.pairs():
        d_ij = model.new_int_var(lo, hi, f"d_{i}_{j}")
        model.add_element(p[i] * n + p[j], flat, d_ij)
        terms.append(d_ij)
        coeffs.append(g)
    model.minimize(cp_model.LinearExpr.weighted_sum(terms, coeffs))
    return model


PROBLEM = Problem(
    name="qap",
    description="Quadratic assignment (QAPLIB), Boolean-product and element encodings",
    download=download,
    instances=instances,
    build=build,
    source="https://coral.ise.lehigh.edu/data-sets/qaplib/",
)

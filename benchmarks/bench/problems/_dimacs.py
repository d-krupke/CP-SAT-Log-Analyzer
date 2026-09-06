"""Shared DIMACS graph parsing and greedy heuristics for the graph problems.

Created 2026-09-06 for the CP-SAT log benchmarks. Private module (the leading
underscore makes ``bench.problems.all_problems`` skip it) used by
``graph_coloring``, ``max_clique`` and ``dominating_set``: they all read the
same ASCII DIMACS edge format and all want the same few greedy helpers.

File format (COLOR ``.col`` and CLIQUE ``.clq`` are identical)::

    c a comment line
    p edge <num_vertices> <num_edges>     # also seen as "p col" / "p edges"
    e <u> <v>                             # 1-based endpoints, undirected
    n <v> <weight>                        # optional vertex weight, ignored here

Every other line is ignored; self-loops and duplicate edges are dropped, so a
parsed :class:`Graph` always has simple, sorted, 0-based edges.

Change this file only if a new instance family needs a different dialect; the
heuristics here are deliberately cheap (they run inside ``build``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Graph:
    """A simple undirected graph; ``edges`` are 0-based pairs with ``u < v``."""

    num_vertices: int
    edges: tuple[tuple[int, int], ...]

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    @property
    def density(self) -> float:
        pairs = self.num_vertices * (self.num_vertices - 1) // 2
        return self.num_edges / pairs if pairs else 0.0

    def neighbours(self) -> list[set[int]]:
        adj: list[set[int]] = [set() for _ in range(self.num_vertices)]
        for u, v in self.edges:
            adj[u].add(v)
            adj[v].add(u)
        return adj

    def bitsets(self) -> list[int]:
        """Adjacency as one Python int per vertex (bit ``w`` set iff ``v~w``)."""
        adj = [0] * self.num_vertices
        for u, v in self.edges:
            adj[u] |= 1 << v
            adj[v] |= 1 << u
        return adj

    def complement(self) -> Graph:
        """The complement graph (used to turn max-clique into an independent-set style model)."""
        adj = self.bitsets()
        n = self.num_vertices
        edges: list[tuple[int, int]] = []
        for u in range(n):
            missing = ~(adj[u] | ((1 << (u + 1)) - 1)) & ((1 << n) - 1)
            while missing:
                bit = missing & -missing
                edges.append((u, bit.bit_length() - 1))
                missing ^= bit
        return Graph(n, tuple(edges))


def parse_graph(path: Path) -> Graph:
    """Parse an ASCII DIMACS ``.col``/``.clq`` file into a :class:`Graph`."""
    num_vertices = 0
    seen: set[tuple[int, int]] = set()
    edges: list[tuple[int, int]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            tag = line[:1].lower()
            if tag == "e":
                parts = line.split()
                if len(parts) < 3:
                    continue
                u, v = int(parts[1]) - 1, int(parts[2]) - 1
                if u == v:
                    continue
                if u > v:
                    u, v = v, u
                if (u, v) in seen:
                    continue
                seen.add((u, v))
                edges.append((u, v))
                num_vertices = max(num_vertices, v + 1)
            elif tag == "p":
                parts = line.split()
                if len(parts) >= 3:
                    num_vertices = max(num_vertices, int(parts[-2]))
    edges.sort()
    return Graph(num_vertices, tuple(edges))


def read_header(path: Path) -> tuple[int, int]:
    """Cheap size probe: ``(num_vertices, num_edges)`` from the ``p`` line."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line[:1].lower() == "p":
                parts = line.split()
                return int(parts[-2]), int(parts[-1])
    raise ValueError(f"no 'p' line in {path}")


def _degree_order_bitsets(graph: Graph) -> tuple[list[int], list[int]]:
    """Adjacency bitsets relabelled so that index 0 is the highest-degree vertex.

    In that space "lowest set bit" == "highest-degree candidate", which makes the
    greedy routines below degree-greedy at O(1) per pick instead of scanning.
    Returns ``(bitsets, order)`` where ``order[i]`` is the original vertex of ``i``.
    """
    adj = graph.bitsets()
    n = graph.num_vertices
    order = sorted(range(n), key=lambda v: -adj[v].bit_count())
    pos = [0] * n
    for index, vertex in enumerate(order):
        pos[vertex] = index
    relabelled = [0] * n
    for vertex in range(n):
        mask, out = adj[vertex], 0
        while mask:
            bit = mask & -mask
            out |= 1 << pos[bit.bit_length() - 1]
            mask ^= bit
        relabelled[pos[vertex]] = out
    return relabelled, order


def greedy_clique(graph: Graph, num_starts: int = 16) -> list[int]:
    """A maximal clique found greedily from the ``num_starts`` densest vertices."""
    if graph.num_vertices == 0:
        return []
    adj, order = _degree_order_bitsets(graph)
    best: list[int] = []
    for start in range(min(graph.num_vertices, max(1, num_starts))):
        clique = [start]
        cand = adj[start]
        while cand:
            bit = cand & -cand
            vertex = bit.bit_length() - 1
            clique.append(vertex)
            cand &= adj[vertex]
        if len(clique) > len(best):
            best = clique
    return sorted(order[i] for i in best)


def edge_clique_cover(graph: Graph) -> list[list[int]]:
    """Cover every edge of ``graph`` by a clique, using as few cliques as possible.

    A clique of size ``s`` replaces ``s*(s-1)/2`` pairwise constraints, which is
    what keeps the colouring and clique models compact on dense graphs; on sparse
    graphs the cover degenerates to ~one clique per edge, i.e. no loss. Two cheap
    greedy strategies are tried because neither dominates: growing cliques
    maximally wins on graphs with huge cliques (hamming10-2: 1015 vs 251554
    cliques), growing them only along not-yet-covered edges wins when cliques
    overlap heavily (keller5: 32868 vs 115902).
    """
    if graph.num_vertices == 0:
        return []
    maximal = _clique_cover(graph, only_new_edges=False)
    fresh = _clique_cover(graph, only_new_edges=True)
    return maximal if len(maximal) <= len(fresh) else fresh


def _clique_cover(graph: Graph, *, only_new_edges: bool) -> list[list[int]]:
    """One greedy pass; see :func:`edge_clique_cover` for the two strategies."""
    n = graph.num_vertices
    adj, order = _degree_order_bitsets(graph)
    uncovered = list(adj)
    cover: list[list[int]] = []
    for start in range(n):
        while uncovered[start]:
            bit = uncovered[start] & -uncovered[start]
            second = bit.bit_length() - 1
            clique = [start, second]
            mask = (1 << start) | bit
            if only_new_edges:
                cand = uncovered[start] & uncovered[second]
            else:
                cand = adj[start] & adj[second]
            while cand:
                bit = cand & -cand
                vertex = bit.bit_length() - 1
                clique.append(vertex)
                mask |= bit
                cand &= uncovered[vertex] if only_new_edges else adj[vertex]
            for vertex in clique:
                uncovered[vertex] &= ~mask
            cover.append([order[i] for i in clique])
    return cover


def dsatur_coloring(graph: Graph) -> list[int]:
    """DSATUR greedy colouring; returns a colour in ``[0, k)`` per vertex."""
    n = graph.num_vertices
    adj = graph.neighbours()
    colors = [-1] * n
    saturation: list[set[int]] = [set() for _ in range(n)]
    degree = [len(adj[v]) for v in range(n)]
    remaining = set(range(n))
    while remaining:
        vertex = max(remaining, key=lambda v: (len(saturation[v]), degree[v]))
        remaining.discard(vertex)
        color = 0
        while color in saturation[vertex]:
            color += 1
        colors[vertex] = color
        for neighbour in adj[vertex]:
            saturation[neighbour].add(color)
    return colors


def dsatur_num_colors(graph: Graph) -> int:
    """Upper bound on the chromatic number from :func:`dsatur_coloring`."""
    if graph.num_vertices == 0:
        return 0
    return max(dsatur_coloring(graph)) + 1

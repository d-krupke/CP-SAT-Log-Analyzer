"""Access to the stored runs of one instance: parsed logs, primal measures, best-known value.

Created 2026-09-27 for the portfolio-importance study. ``InstanceRuns`` loads every
``runs/<problem>/<instance>/*.json`` once, parses logs lazily and derives the best-known
objective over all runs (plus the 60 s corpus run when present) so that gaps are
comparable between experiments.
"""

from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

from cpsat_logutils import CpSatLog, parse_log

from .evaluate import Primal, primal, sense, trajectory
from .runner import ROOT, RUNS, RunConfig


class InstanceRuns:
    def __init__(self, problem: str, instance: str):
        self.problem, self.instance = problem, instance
        self.dir = RUNS / problem / instance
        self.metas: dict[str, dict] = {}
        for j in sorted(self.dir.glob("*.json")):
            self.metas[j.stem] = json.loads(j.read_text())
        self._logs: dict[str, CpSatLog] = {}

    def log(self, key: str) -> CpSatLog:
        if key not in self._logs:
            self._logs[key] = parse_log((self.dir / f"{key}.txt").read_text())
        return self._logs[key]

    def has(self, cfg: RunConfig) -> bool:
        return cfg.key in self.metas

    def find(self, cfg: RunConfig) -> str | None:
        """Key of a stored run equivalent to ``cfg``: same settings and the same *set* of
        whitelisted subsolvers (CP-SAT launches them all at once, so the order in the list
        is irrelevant and runs can be reused across metrics)."""
        if cfg.key in self.metas:
            return cfg.key
        for key, m in self.metas.items():
            c = m["config"]
            if (c["workers"], c["seed"], c["time_limit"], c["num_full"]) != (cfg.workers, cfg.seed, cfg.time_limit, cfg.num_full):
                continue
            if set(c["subsolvers"]) == set(cfg.subsolvers) and set(c["ignore"]) == set(cfg.ignore) and c["params"] == cfg.params:
                return key
        return None

    @cached_property
    def sense(self) -> int:
        for key in self.metas:
            return sense(self.log(key))
        return 1

    @cached_property
    def best_known(self) -> float:
        """Best objective over all stored runs that found a solution, plus the corpus run."""
        values = [m["objective"] for key, m in self.metas.items()
                  if m.get("objective") is not None and trajectory(self.log(key))]
        for j in (ROOT / "logs" / self.problem).glob(f"{self.instance}__*.json"):
            meta = json.loads(j.read_text())
            if meta.get("objective") is not None and meta.get("status") in ("OPTIMAL", "FEASIBLE"):
                values.append(meta["objective"])
        if not values:
            return 0.0
        return min(values) if self.sense > 0 else max(values)

    def primal(self, cfg: RunConfig) -> Primal:
        key = self.find(cfg)
        if key is None:
            raise KeyError(cfg.key)
        return primal(self.log(key), self.best_known, cfg.time_limit)


def all_instances() -> list[tuple[str, str]]:
    out = []
    for p in sorted(Path(RUNS).glob("*")):
        for i in sorted(p.glob("*")):
            if any(i.glob("*.json")):
                out.append((p.name, i.name))
    return out

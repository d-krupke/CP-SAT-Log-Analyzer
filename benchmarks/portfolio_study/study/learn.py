"""Data-fitted importance: ridge regression from per-subsolver log features to the ablation
ground truth, evaluated leave-one-instance-out.

Created 2026-09-27 for the portfolio-importance study. Features are normalized *within*
an instance (shares, ranks), so the fitted weights transfer between instances of very
different scale. The target is the negated, within-instance z-scored primal integral of the
solo run (2 workers, only that subsolver): high = the subsolver alone does well. The
resulting weights are meant to be frozen into ``metrics.learned`` once they look stable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signals import SubsolverSignals

FEATURES = [
    "improvement_share", "count_share", "late_count_share", "found_first", "found_best",
    "last_rank_share", "bounds_share", "shared_bounds_share", "conflict_share", "default_pos",
]


def _share(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    return {k: (v / total if total > 0 else 0.0) for k, v in values.items()}


def feature_rows(sig: dict[str, SubsolverSignals]) -> dict[str, np.ndarray]:
    """Feature vector (order = FEATURES) per subsolver, normalized within the instance."""
    n = len(sig)
    imp = _share({k: s.improvement_share for k, s in sig.items()})
    cnt = _share({k: float(s.n_improvements) for k, s in sig.items()})
    late = _share({k: float(s.n_late_improvements) for k, s in sig.items()})
    lb = _share({k: float(s.n_bounds) for k, s in sig.items()})
    shared = _share({k: float(s.shared_bounds) for k, s in sig.items()})
    confl = _share({k: float(s.conflicts) for k, s in sig.items()})
    rows = {}
    for k, s in sig.items():
        rows[k] = np.array([
            imp[k], cnt[k], late[k], float(s.found_first), float(s.found_best), s.last_rank_share,
            lb[k], shared[k], confl[k], 1.0 - s.default_rank / max(n, 1),
        ])
    return rows


def zscore(values: dict[str, float]) -> dict[str, float]:
    arr = np.array(list(values.values()))
    sd = arr.std()
    return {k: ((v - arr.mean()) / sd if sd > 0 else 0.0) for k, v in values.items()}


@dataclass
class Fit:
    weights: np.ndarray
    intercept: float

    def score(self, x: np.ndarray) -> float:
        return float(x @ self.weights + self.intercept)


def ridge(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> Fit:
    Xc = np.hstack([X, np.ones((len(X), 1))])
    reg = alpha * np.eye(Xc.shape[1])
    reg[-1, -1] = 0.0
    w = np.linalg.solve(Xc.T @ Xc + reg, Xc.T @ y)
    return Fit(w[:-1], float(w[-1]))


def loio(datasets: list[tuple[dict[str, np.ndarray], dict[str, float]]], alpha: float = 1.0) -> list[list[str]]:
    """Leave-one-instance-out: for each instance, the ordering predicted by a model fitted on
    the others. ``datasets`` holds (features, target) per instance."""
    orders = []
    for hold in range(len(datasets)):
        X = np.vstack([x for i, (f, t) in enumerate(datasets) if i != hold for x in f.values()])
        y = np.array([t[k] for i, (f, t) in enumerate(datasets) if i != hold for k in f])
        fit = ridge(X, y, alpha)
        f, _ = datasets[hold]
        orders.append(sorted(f, key=lambda k: -fit.score(f[k])))
    return orders

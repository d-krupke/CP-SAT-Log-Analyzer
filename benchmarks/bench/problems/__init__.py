"""Registry of problem modules: every ``bench/problems/<name>.py`` with a ``PROBLEM``."""

from __future__ import annotations

import importlib
import pkgutil

from ..base import Problem


def all_problems() -> dict[str, Problem]:
    problems: dict[str, Problem] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        problem = getattr(module, "PROBLEM", None)
        if problem is not None:
            problems[problem.name] = problem
    return problems

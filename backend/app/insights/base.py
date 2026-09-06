"""The trigger framework behind the colored insight boxes of the Overview.

Created 2026-09 when the insight rules moved out of ``knowledge/insights.toml``
into code: a threshold plus a format string could not express much, and a TOML
section gives no hint of what else one *could* look at. A trigger is now a small
class that sees the whole analysis and writes its own sentence.

Writing one::

    class BoundStalled(Trigger):
        '''Why this is worth saying (for the next reader of this file).'''

        level = "info"                  # info | good | warn | bad
        title = "Bound stalled early"
        max_share = 0.5                 # thresholds live next to the check

        def check(self, ctx: Context) -> Insight | None:
            if not ctx.progress.bounds or ctx.walltime is None:
                return None
            last = ctx.progress.bounds[-1]
            if last.time >= self.max_share * ctx.walltime:
                return None
            return self.fire(f"The bound last improved at {last.time:.1f}s.", [last.line])

Put the class in any module under ``triggers/``; it is discovered by import, so
there is nothing to register. Return ``None`` to stay quiet, or ``self.fire(text,
lines)`` where ``text`` is Markdown (indentation is stripped) and ``lines`` are
the log lines the claim rests on - the UI turns them into jump links, so a
trigger that cannot point at evidence is usually saying too much.

Guidance for the text: describe what *this* log shows and let the reader draw
the conclusion. Advice that a different log would contradict does not belong in
a box that fires automatically.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import re
from collections.abc import Sequence
from dataclasses import dataclass
from inspect import cleandoc
from typing import TYPE_CHECKING, ClassVar

from cpsatlog import CpSatLog
from cpsatlog.schema import Loc, ResponseSummary
from pydantic import BaseModel, Field

from ..solver_info import num_workers

if TYPE_CHECKING:
    from ..analysis import ProgressSeries
    from ..hints import HintReport

LEVELS = ("info", "good", "warn", "bad")

logger = logging.getLogger(__name__)


class Insight(BaseModel):
    """One box in the Overview: what a trigger decided to say about this log."""

    level: str  # info | good | warn | bad
    title: str
    text: str
    lines: list[int] = Field(default_factory=list)


@dataclass(frozen=True)
class Context:
    """Everything a trigger may look at, with the few shortcuts every second one needs."""

    log: CpSatLog
    progress: ProgressSeries
    hint: HintReport

    @property
    def response(self) -> ResponseSummary | None:
        return self.log.response

    @property
    def status(self) -> str | None:
        """`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN` - or None if the log was cut off."""
        response = self.log.response
        return response.status.value if response and response.status else None

    @property
    def status_lines(self) -> list[int]:
        response = self.log.response
        return [response.status.line] if response and response.status else []

    @property
    def walltime(self) -> float | None:
        response = self.log.response
        return response.walltime.value if response and response.walltime else None

    @property
    def num_workers(self) -> Loc[int] | None:
        """Workers and the line that states them - the same answer the Workers tile shows."""
        return num_workers(self.log)


TRIGGERS: list[type[Trigger]] = []


class Trigger:
    """Base class of every insight trigger; see the module docstring for how to write one."""

    level: ClassVar[str] = "info"
    title: ClassVar[str] = ""
    #: Sorting key of the boxes; lower comes first. See ``triggers/__init__.py``.
    order: ClassVar[int] = 50
    #: Stable name, derived from the class name; used in tests and log messages.
    key: ClassVar[str] = ""
    _index: ClassVar[int] = 0

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.key = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        cls._index = len(TRIGGERS)
        TRIGGERS.append(cls)

    def check(self, ctx: Context) -> Insight | None:
        """Fire (``self.fire(...)``) or stay quiet (``None``)."""
        raise NotImplementedError

    def fire(self, text: str, lines: Sequence[int] = (), *, level: str | None = None) -> Insight:
        """Build the box. ``text`` is Markdown; its common indentation is removed."""
        return Insight(
            level=level or self.level,
            title=self.title,
            text=cleandoc(text).strip(),
            lines=list(lines),
        )


_loaded: list[Trigger] | None = None


def all_triggers() -> list[Trigger]:
    """Every trigger under ``triggers/``, instantiated once and in display order."""
    global _loaded
    if _loaded is None:
        from . import triggers

        for module in pkgutil.iter_modules(triggers.__path__):
            importlib.import_module(f"{triggers.__name__}.{module.name}")
        _loaded = [cls() for cls in sorted(TRIGGERS, key=lambda c: (c.order, c._index))]
    return _loaded


def build_insights(log: CpSatLog, progress: ProgressSeries, hint: HintReport) -> list[Insight]:
    """Run every trigger over one log.

    A trigger that raises is skipped with a warning rather than failing the whole analysis:
    logs are user input and a new trigger will meet shapes it did not expect. The corpus test
    fails on such a warning, so this never hides a bug for long.
    """
    ctx = Context(log=log, progress=progress, hint=hint)
    out: list[Insight] = []
    for trigger in all_triggers():
        try:
            insight = trigger.check(ctx)
        except Exception:
            logger.warning("insight trigger %r failed", trigger.key, exc_info=True)
            continue
        if insight is not None:
            out.append(insight)
    return out

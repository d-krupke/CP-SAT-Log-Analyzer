"""What is wrong with the log itself, before anything is read out of it.

Users paste logs that were killed mid-run, cut off at the top, mixed with their
own prints, or are not CP-SAT logs at all. Everything derived from such a log is
partial, so it is said first (``order = 10``) - and the unrecognized lines are
highlighted in the raw log view as well.
"""

from __future__ import annotations

from cpsat_logutils import CpSatLog

from ..base import Context, Insight, Trigger


def looks_like_cpsat(log: CpSatLog) -> bool:
    """Did anything CP-SAT prints parse at all? If not, no other box makes sense."""
    return bool(log.solver or log.initial_model or log.response or log.search)


class NotACpSatLog(Trigger):
    """The common cause is not a wrong paste but a missing `log_search_progress`."""

    order = 10
    level = "bad"
    title = "This does not look like a CP-SAT log"

    def check(self, ctx: Context) -> Insight | None:
        if looks_like_cpsat(ctx.log) or not ctx.log.unparsed:
            return None
        return self.fire(
            """
            Nothing that CP-SAT prints was found in this text - no solver header, no model, no
            search and no response summary. Two common causes: the output of a different tool
            was pasted, or `log_search_progress` was not enabled, in which case CP-SAT prints
            almost nothing. Set `solver.parameters.log_search_progress = True` (and keep the
            default `log_to_stdout`) and run again.
            """,
            [ctx.log.unparsed[0].span.start],
        )


class LogTruncated(Trigger):
    order = 10
    level = "warn"
    title = "Log ends before the response summary"

    def check(self, ctx: Context) -> Insight | None:
        if not looks_like_cpsat(ctx.log) or ctx.log.response is not None:
            return None
        last = ctx.log.blocks[-1].span.end if ctx.log.blocks else ctx.log.num_lines
        return self.fire(
            f"""
            The log stops at line {last} without a `CpSolverResponse summary`, so the run was
            killed, is still going, or the output was cut off. Status, objective, bound and
            wall time are unknown; everything shown here is what the log contains up to that
            line.
            """,
            [last],
        )


class HeadMissing(Trigger):
    order = 10
    level = "warn"
    title = "Beginning of the log is missing"

    def check(self, ctx: Context) -> Insight | None:
        if not looks_like_cpsat(ctx.log) or ctx.log.solver is not None:
            return None
        first = ctx.log.blocks[0].span.start if ctx.log.blocks else 1
        return self.fire(
            """
            The log starts after the solver header, so the OR-Tools version, the parameters you
            set and the initial model are unknown, and the checks that depend on them are
            skipped. Paste the log from the first `Starting CP-SAT solver` line on to get the
            full analysis.
            """,
            [first],
        )


class UnrecognizedLines(Trigger):
    """Any unrecognized line is worth reporting: a healthy log has none."""

    order = 10
    level = "warn"
    title = "Parts of the log were not recognized"
    min_lines = 1

    def check(self, ctx: Context) -> Insight | None:
        count = sum(len(block.lines) for block in ctx.log.unparsed)
        if not looks_like_cpsat(ctx.log) or count < self.min_lines:
            return None
        places = len(ctx.log.unparsed)
        first = ctx.log.unparsed[0].span.start
        return self.fire(
            f"""
            {count} line(s) in {places} place(s) could not be assigned to any known section,
            starting at line {first}; they are marked in the log on the right. Usually this is
            your own output mixed into the log, a line-prefix added by a logging framework, or
            lines clipped by a terminal. If it is plain CP-SAT output, the parser is missing a
            section - please report the log.
            """,
            [block.span.start for block in ctx.log.unparsed[:3]],
        )

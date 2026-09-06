"""Builders for deliberately damaged CP-SAT logs.

Created 2026-09-06: users paste logs that are truncated by a killed process, clipped by a
terminal, prefixed by a logging framework, mixed with their own prints, or not CP-SAT logs at
all. The parser must survive all of that with its line anchoring intact, so the robustness
tests (``test_broken.py`` here, ``test_broken.py`` in the backend) build their inputs from a
healthy example log through the deterministic transformations below.

Each function takes and returns log text; ``damaged_variants`` bundles them into the named set
the tests parametrize over. Add a transformation here when a new way of breaking a log shows
up in an issue.
"""

from __future__ import annotations

NOT_A_LOG = "Hello, this is not a log at all.\nJust some text somebody pasted.\n"
TRACEBACK = (
    'Traceback (most recent call last):\n  File "solve.py", line 12, in <module>\n'
    "    solver.Solve(model)\nRuntimeError: boom\n"
)


def truncate(text: str, fraction: float) -> str:
    """Keep the first ``fraction`` of the lines: the run was killed or is still going."""
    lines = text.split("\n")
    return "\n".join(lines[: max(1, int(len(lines) * fraction))])


def drop_head(text: str, lines: int) -> str:
    """Remove the first ``lines`` lines: somebody pasted only the tail of the log."""
    return "\n".join(text.split("\n")[lines:])


def clip_width(text: str, width: int) -> str:
    """Cut every line after ``width`` characters, as a narrow terminal or a log viewer does."""
    return "\n".join(line[:width] for line in text.split("\n"))


def prefix_lines(text: str, prefix: str) -> str:
    """Put ``prefix`` in front of every line (logging framework, MiniZinc's ``%% ``)."""
    return "\n".join(prefix + line for line in text.split("\n"))


def interleave(text: str, every: int, message: str = ">>> my own print") -> str:
    """Insert a line of the user's own output every ``every`` lines."""
    out: list[str] = []
    for i, line in enumerate(text.split("\n")):
        out.append(line)
        if i % every == 0:
            out.append(message)
    return "\n".join(out)


def duplicate(text: str) -> str:
    """Two runs appended to the same file."""
    return text + "\n" + text


def crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


def with_nul(text: str) -> str:
    """Binary damage: NUL bytes in the middle of the log."""
    return text.replace("s", "\x00", 200)


def damaged_variants(text: str) -> dict[str, str]:
    """The named set of damaged logs the robustness tests run over."""
    return {
        "empty": "",
        "whitespace_only": "   \n\n\t\n",
        "not_a_log": NOT_A_LOG,
        "traceback": TRACEBACK,
        "truncated_10%": truncate(text, 0.10),
        "truncated_50%": truncate(text, 0.50),
        "truncated_90%": truncate(text, 0.90),
        "head_dropped": drop_head(text, 40),
        "clipped_38_chars": clip_width(text, 38),
        "timestamp_prefixed": prefix_lines(text, "2026-09-06 10:00:00 INFO cpsat | "),
        "minizinc_prefixed": prefix_lines(text, "%% "),
        "own_prints": interleave(text, 37),
        "two_runs": duplicate(text),
        "crlf": crlf(text),
        "nul_bytes": with_nul(text),
        "one_huge_line": "x" * 100_000,
    }

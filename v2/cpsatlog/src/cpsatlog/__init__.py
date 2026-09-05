"""cpsatlog – parse CP-SAT solver logs into line-anchored pydantic models.

Usage::

    from cpsatlog import parse_log
    log = parse_log(open("solver.log").read())
    print(log.response.status.value, "found at line", log.response.status.line)
    print(log.model_dump_json(indent=2))   # fully JSON serialisable

Design (see ``schema/`` and ``parsers/``):

* ``splitter``  – cuts the text into blank-line separated chunks with line numbers.
* ``parsers``   – one ``BlockParser`` per section, tried in registry order.
* ``assemble``  – merges chunks into the ``CpSatLog`` root and builds the block index.

Every value knows its line (``Loc``) and every section its ``LineSpan`` so a UI
can map raw text to data and back. Sections that are not in the log are ``None``.
"""

from .assemble import parse_log
from .schema import CpSatLog

__all__ = ["CpSatLog", "parse_log"]
__version__ = "0.1.0"

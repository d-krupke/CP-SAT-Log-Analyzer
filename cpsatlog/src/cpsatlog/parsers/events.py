"""Parse a single search progress line into a ``SearchEvent``.

Formats (from ``cp_model_solver_logging.cc`` / ``synchronization.cc``):

* ``#12      0.71s best:17    next:[1,16]     quick_restart_no_lp fixed_bools:0/11849``
* ``#Bound   1.30s best:inf   next:[8,14]     max_lp initial_propagation``
* ``#Bound   0.66s best:inf   next:[]         objective_lb_search`` (empty when lb > ub)
* ``#Model   0.26s var:125/126 constraints:162/162 [skipped_logs=5]``
* ``#Model   0.01s var:485/485 constraints:263/263 compo:375,35,33,22,20``
* ``#Done    2.98s objective_lb_search_no_lp``
* ``#1       0.05s no_lp`` (satisfaction problems: no objective)

The subsolver name is the leading ``[A-Za-z0-9_]`` run of the message, exactly
as CP-SAT itself extracts it for the ``Solutions`` table. ``#Model`` lines carry no
worker name, so nothing is extracted from them (``compo:`` used to be read as a
worker called ``compo``).
"""

from __future__ import annotations

import re

from ..schema.search import SearchEvent
from ..text import NUMBER_TOKEN, parse_float, parse_int

_NUM = rf"(?:{NUMBER_TOKEN}|inf|-inf|nan)"
_EVENT = re.compile(r"^#(?P<label>\S+)\s+(?P<time>[\d.]+)s\s*(?P<rest>.*)$")
_OBJECTIVE = re.compile(
    rf"^best:(?P<best>{_NUM})\s+next:\[(?:(?P<lb>{_NUM}),(?P<ub>{_NUM}))?\]\s*(?P<rest>.*)$"
)
_MODEL = re.compile(
    r"^var:(?P<v>\d+)/(?P<vt>\d+)\s+constraints:(?P<c>\d+)/(?P<ct>\d+)\s*(?P<rest>.*)$"
)
_SKIPPED = re.compile(r"\[skipped_logs=(?P<n>\d+)\]")
_COMPO = re.compile(r"compo:(?P<sizes>\d+(?:,\d+)*)(?P<trunc>,\.\.\.)?")
_TAG = re.compile(r"\[(?P<tag>[a-z_]+)\]")
_SUBSOLVER = re.compile(r"^(?P<name>[A-Za-z0-9_]+)")


def parse_event(line: str, line_no: int) -> SearchEvent | None:
    m = _EVENT.match(line)
    if not m:
        return None
    label, rest = m.group("label"), m.group("rest").strip()
    time = parse_float(m.group("time")) or 0.0
    event = SearchEvent(line=line_no, kind="other", label=f"#{label}", time=time)

    if label.isdigit():
        event.kind = "solution"
        event.solution_index = int(label)
    elif label == "Bound":
        event.kind = "bound"
    elif label == "Model":
        event.kind = "model"
    elif label == "Done":
        event.kind = "done"

    if o := _OBJECTIVE.match(rest):
        event.objective = _finite(o.group("best"))
        if event.objective is None and "inf" in o.group("best"):
            event.objective_infinite = o.group("best")
        event.next_lb = _finite(o.group("lb")) if o.group("lb") else None
        event.next_ub = _finite(o.group("ub")) if o.group("ub") else None
        rest = o.group("rest").strip()
    elif mm := _MODEL.match(rest):
        event.model_vars = parse_int(mm.group("v"))
        event.model_vars_total = parse_int(mm.group("vt"))
        event.model_constraints = parse_int(mm.group("c"))
        event.model_constraints_total = parse_int(mm.group("ct"))
        rest = mm.group("rest").strip()
        if compo := _COMPO.search(rest):
            event.model_components = [int(n) for n in compo.group("sizes").split(",")]
            event.model_components_truncated = compo.group("trunc") is not None
            rest = _COMPO.sub("", rest).strip()

    if s := _SKIPPED.search(rest):
        event.skipped_logs = int(s.group("n"))
        rest = _SKIPPED.sub("", rest).strip()
    event.tags = [t.group("tag") for t in _TAG.finditer(rest)]
    event.message = rest
    if event.kind != "model" and (sub := _SUBSOLVER.match(rest)):
        event.subsolver = sub.group("name")
    return event


def _finite(token: str | None) -> float | None:
    if token is None:
        return None
    value = parse_float(token)
    if value is None or value != value or value in (float("inf"), float("-inf")):
        return None
    return value

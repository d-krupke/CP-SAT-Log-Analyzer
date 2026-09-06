"""Loader for the editable knowledge base in ``v2/knowledge/*.toml``.

Created with the v2 analyzer so that all CP-SAT domain knowledge (explanations,
parameter advice, subsolver descriptions, table columns, ...) lives in plain
TOML files that a CP-SAT expert can edit without touching code. The insight
boxes are the exception - they are Python classes, see ``app/insights``. See
``v2/knowledge/README.md`` for the file map.

Usage::

    from .knowledge import load
    blocks = load("blocks")["blocks"]          # dict[str, str]

Files are re-read when their modification time changes, so edits show up on the
next request without restarting the server. ``python -m app.knowledge`` checks
that every file parses and has the expected top-level sections.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(
    os.environ.get("KNOWLEDGE_DIR") or Path(__file__).resolve().parents[2] / "knowledge"
)

# file stem -> required top-level keys
REQUIRED: dict[str, tuple[str, ...]] = {
    "blocks": ("blocks", "cards"),
    "tables": ("tables",),
    "response_fields": ("response_fields",),
    "subsolvers": ("roles", "subsolvers", "patterns", "categories"),
    "constraints": ("constraints", "complexity"),
    "model": ("domain_size",),
    "messages": ("messages",),
    "parameters": ("safe", "unknown", "advice", "warning"),
    "metrics": (),
    "examples": ("examples",),
}

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def path_of(name: str) -> Path:
    return KNOWLEDGE_DIR / f"{name}.toml"


def load(name: str) -> dict[str, Any]:
    """Parse ``<name>.toml``; cached per modification time."""
    path = path_of(name)
    mtime = path.stat().st_mtime
    cached = _cache.get(name)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    _cache[name] = (mtime, data)
    return data


def validate() -> list[str]:
    """Return human-readable problems (empty list = everything loads)."""
    problems: list[str] = []
    for name, keys in REQUIRED.items():
        path = path_of(name)
        if not path.is_file():
            problems.append(f"{path}: file is missing")
            continue
        try:
            data = load(name)
        except (tomllib.TOMLDecodeError, OSError) as exc:
            problems.append(f"{path}: {exc}")
            continue
        for key in keys:
            if key not in data:
                problems.append(f"{path}: missing section [{key}]")
    problems.extend(_validate_subsolvers())
    problems.extend(_validate_model_indicators())
    return problems


def _validate_subsolvers() -> list[str]:
    try:
        data = load("subsolvers")
    except Exception:  # noqa: BLE001 - reported by validate() already
        return []
    roles = set(data.get("roles", {}))
    out = []
    entries = list(data.get("subsolvers", {}).items())
    entries += [(f"pattern {p.get('pattern')}", p) for p in data.get("patterns", [])]
    for key, entry in entries:
        for field in ("summary", "details", "role"):
            if not entry.get(field):
                out.append(f"subsolvers.toml: {key} lacks '{field}'")
        if entry.get("role") not in roles:
            out.append(f"subsolvers.toml: {key} has unknown role {entry.get('role')!r}")
    return out


def _validate_model_indicators() -> list[str]:
    out = []
    try:
        cons, model = load("constraints"), load("model")
    except Exception:  # noqa: BLE001
        return out
    levels = cons.get("complexity", {})
    for key, entry in cons.get("constraints", {}).items():
        if not entry.get("summary"):
            out.append(f"constraints.toml: {key} lacks 'summary'")
        if entry.get("complexity") not in levels:
            out.append(
                f"constraints.toml: {key} has unknown complexity {entry.get('complexity')!r}"
            )
    domain = model.get("domain_size", {})
    for text in ("holes", "truncated", "summary", "constant"):
        if not domain.get(text):
            out.append(f"model.toml: [domain_size] lacks '{text}'")
    sizes = [lv.get("max_size") for lv in domain.get("level", [])]
    if not sizes or sizes[-1] is not None:
        out.append("model.toml: the last [[domain_size.level]] must have no max_size")
    if any(a is None or (b is not None and a >= b) for a, b in zip(sizes, sizes[1:], strict=False)):
        out.append("model.toml: [[domain_size.level]] max_size values must increase")
    for lv in domain.get("level", []) + list(levels.values()):
        if lv.get("color") not in {"good", "info", "warn", "bad"}:
            out.append(
                f"knowledge: level {lv.get('label')!r} has unknown color {lv.get('color')!r}"
            )
    return out


def main() -> int:
    problems = validate()
    for p in problems:
        print("ERROR:", p)
    if problems:
        return 1
    print(f"OK: all knowledge files in {KNOWLEDGE_DIR} load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

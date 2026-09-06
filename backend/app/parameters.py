"""Explain the parameters a user overrode (the ``Parameters:`` line).

Documentation comes from ``data/sat_parameters.json`` (generated from
OR-Tools' ``sat_parameters.proto`` by ``tools/extract_sat_parameters.py``).
Advice and warning rules come from ``knowledge/parameters.toml``; this
module only evaluates the rules (first matching ``[[warning]]`` wins).
"""

from __future__ import annotations

import fnmatch
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .knowledge import load

DATA_FILE = Path(__file__).parent / "data" / "sat_parameters.json"


class ParameterInfo(BaseModel):
    name: str
    value: Any
    known: bool
    type: str | None = None
    default: str | None = None
    section: str | None = None
    doc: str = ""
    enum_values: dict[str, str] = Field(default_factory=dict)
    advice: str | None = None
    warning: str | None = None


@lru_cache(maxsize=1)
def load_docs() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"parameters": {}, "enums": {}, "sections": []}
    return json.loads(DATA_FILE.read_text())


def describe_parameter(name: str, value: Any) -> ParameterInfo:
    docs = load_docs()
    meta = docs["parameters"].get(name)
    advice = load("parameters")["advice"].get(name)
    info = ParameterInfo(name=name, value=value, known=meta is not None, advice=advice)
    if meta is not None:
        info.type = meta["type"]
        info.default = meta["default"]
        info.section = meta["section"]
        info.doc = meta["doc"]
        if meta.get("enum"):
            info.enum_values = docs["enums"].get(meta["enum"], {})
    info.warning = _warning(name, value, info)
    return info


def _as_list(x: Any) -> list[str]:
    return [x] if isinstance(x, str) else list(x or [])


def _rule_matches(rule: dict[str, Any], name: str, value: Any) -> bool:
    if "parameter" in rule:
        if name not in _as_list(rule["parameter"]):
            return False
        return "value" not in rule or rule["value"] == value
    if "pattern" in rule:
        return any(fnmatch.fnmatch(name, p) for p in _as_list(rule["pattern"]))
    if "prefix" in rule:
        return name.startswith(tuple(_as_list(rule["prefix"])))
    return False


def _warning(name: str, value: Any, info: ParameterInfo) -> str | None:
    rules = load("parameters")
    if not info.known:
        return rules["unknown"]
    if name in rules["safe"]:
        return None
    for rule in rules["warning"]:
        if _rule_matches(rule, name, value):
            return rule["text"]
    return None


def describe_all(parameters: dict[str, Any]) -> list[ParameterInfo]:
    return [describe_parameter(name, value) for name, value in parameters.items()]

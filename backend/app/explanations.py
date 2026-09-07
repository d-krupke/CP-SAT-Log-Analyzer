"""Explanations served to the UI, read from ``knowledge/*.toml``.

This module only shapes the knowledge files into the API models; the texts
themselves live in ``blocks.toml``, ``tables.toml``, ``response_fields.toml``,
``subsolvers.toml``, ``constraints.toml``, ``model.toml`` and ``messages.toml`` (see
``knowledge/README.md``). Keys are the stable identifiers used by the parser
(block kinds, ``table_id``s, column names, response fields, subsolver names).
"""

from __future__ import annotations

import fnmatch

from pydantic import BaseModel, Field

from .knowledge import load


class TableDoc(BaseModel):
    summary: str
    columns: dict[str, str] = Field(default_factory=dict)


class SubsolverDoc(BaseModel):
    summary: str
    details: str = ""
    role: str = "exact"


class SubsolverPattern(SubsolverDoc):
    pattern: str


class ConstraintDoc(BaseModel):
    summary: str
    # The long version: which propagator the kind gets, what presolve does with
    # it and what the LP sees. Shown on hover, so it may be a paragraph.
    details: str = ""
    complexity: str = "linear"
    # Enforced ("reified") constraints are a different animal than their plain
    # counterparts - `b => 3x <= 7` is an indicator constraint with a big-M LP
    # relaxation - so a kind may classify its `#enforced` share separately.
    enforced_complexity: str | None = None
    enforced_summary: str = ""


class LevelDoc(BaseModel):
    label: str
    color: str = "info"
    text: str = ""


class DomainSizeLevel(LevelDoc):
    id: str
    max_size: int | None = Field(default=None, description="Inclusive upper bound; None = rest")


class DomainDocs(BaseModel):
    levels: list[DomainSizeLevel]
    holes: str
    truncated: str
    summary: str
    constant: str


class Explanations(BaseModel):
    blocks: dict[str, str]
    cards: dict[str, str]
    tables: dict[str, TableDoc]
    response_fields: dict[str, str]
    subsolvers: dict[str, SubsolverDoc]
    subsolver_patterns: list[SubsolverPattern]
    subsolver_roles: dict[str, str]
    subsolver_categories: dict[str, str]
    constraints: dict[str, ConstraintDoc]
    constraint_complexity: dict[str, LevelDoc]
    domains: DomainDocs
    messages: dict[str, str]


def subsolver_docs() -> dict[str, SubsolverDoc]:
    return {k: SubsolverDoc(**v) for k, v in load("subsolvers")["subsolvers"].items()}


def describe_subsolver(name: str) -> SubsolverDoc | None:
    """Exact key, then the longest key ``name`` starts with (``key_...``), then patterns."""
    docs = subsolver_docs()
    if name in docs:
        return docs[name]
    prefixes = [k for k in docs if name.startswith(k + "_")]
    if prefixes:
        return docs[max(prefixes, key=len)]
    for pat in load("subsolvers")["patterns"]:
        if fnmatch.fnmatch(name, pat["pattern"]):
            return SubsolverDoc(summary=pat["summary"], details=pat["details"], role=pat["role"])
    return None


def all_explanations() -> Explanations:
    blocks, subs = load("blocks"), load("subsolvers")
    cons, dom = load("constraints"), load("model")["domain_size"]
    return Explanations(
        blocks=blocks["blocks"],
        cards=blocks["cards"],
        tables={k: TableDoc(**v) for k, v in load("tables")["tables"].items()},
        response_fields=load("response_fields")["response_fields"],
        subsolvers=subsolver_docs(),
        subsolver_patterns=[SubsolverPattern(**p) for p in subs["patterns"]],
        subsolver_roles=subs["roles"],
        subsolver_categories=subs["categories"],
        constraints={k: ConstraintDoc(**v) for k, v in cons["constraints"].items()},
        constraint_complexity={k: LevelDoc(**v) for k, v in cons["complexity"].items()},
        domains=DomainDocs(levels=dom["level"], **{k: v for k, v in dom.items() if k != "level"}),
        messages=load("messages")["messages"],
    )

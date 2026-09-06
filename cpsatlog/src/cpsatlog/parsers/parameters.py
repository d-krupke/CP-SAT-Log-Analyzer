"""Parse the ``Parameters:`` line (protobuf short debug string of SatParameters).

The format is ``key: value key: value nested { key: value } ...``. Strings are
double quoted, enums are bare identifiers, repeated fields repeat the key.
Repeated keys are collected into lists. Only the parameters that differ from
their defaults are printed by CP-SAT.
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(
    r"""
    (?P<string>"(?:[^"\\]|\\.)*")
    |(?P<punct>[{}\[\]:,])
    |(?P<word>[^\s{}\[\]:,"]+)
    """,
    re.VERBOSE,
)


def _tokens(text: str) -> list[str]:
    return [m.group(0) for m in _TOKEN.finditer(text)]


def _scalar(token: str) -> Any:
    if token.startswith('"'):
        return bytes(token[1:-1], "utf-8").decode("unicode_escape")
    low = token.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|-?inf|nan", token):
        return float(token)
    return token


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> str:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def message(self, closing: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while (token := self.peek()) is not None:
            if token == closing:
                self.next()
                break
            key = self.next()
            value: Any
            nxt = self.peek()
            if nxt == ":":
                self.next()
                nxt = self.peek()
            if nxt == "{":
                self.next()
                value = self.message("}")
            elif nxt == "[":
                self.next()
                value = self.list_value()
            elif nxt is None:
                value = None
            else:
                value = _scalar(self.next())
            if key in result:
                if not isinstance(result[key], list) or not result.get(f"__list__{key}"):
                    result[key] = [result[key]]
                    result[f"__list__{key}"] = True
                result[key].append(value)
            else:
                result[key] = value
        return {k: v for k, v in result.items() if not k.startswith("__list__")}

    def list_value(self) -> list[Any]:
        items: list[Any] = []
        while (token := self.peek()) is not None and token != "]":
            if token == ",":
                self.next()
                continue
            if token == "{":
                self.next()
                items.append(self.message("}"))
            else:
                items.append(_scalar(self.next()))
        if self.peek() == "]":
            self.next()
        return items


def parse_parameters(text: str) -> dict[str, Any]:
    """Parse the text after ``Parameters:`` into a nested dict."""
    return _Parser(_tokens(text)).message()

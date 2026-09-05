"""Low-level text helpers shared by all block parsers.

Created for the v2 pydantic-based CP-SAT log parser. CP-SAT prints numbers with
`'` as thousands separator (e.g. ``3'020``), durations with unit suffixes
(``524.50ms``) and `NA`/`inf` placeholders. Everything that turns such a token
into a Python value lives here so that the block parsers stay declarative.
"""

from __future__ import annotations

import re

NUMBER_TOKEN = r"-?(?:\d[\d']*)(?:\.\d+)?(?:[eE][+-]?\d+)?"
_NUMBER_RE = re.compile(rf"^{NUMBER_TOKEN}$")
_INT_RE = re.compile(r"^-?\d[\d']*$")
_DURATION_RE = re.compile(r"^(?P<num>-?\d+(?:\.\d+)?)(?P<unit>ns|us|ms|s|m|h)?$")

_DURATION_FACTORS = {
    "ns": 1e-9,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    None: 1.0,
}


def clean_number(token: str) -> str:
    """Remove thousands separators and surrounding whitespace."""
    return token.strip().replace("'", "")


def parse_int(token: str) -> int | None:
    """``"3'020"`` -> ``3020``; returns ``None`` for non-integers."""
    token = token.strip()
    if not _INT_RE.match(token):
        return None
    return int(clean_number(token))


def parse_float(token: str) -> float | None:
    """Parse a float that may use `'` separators or be ``inf``/``-inf``/``nan``."""
    token = clean_number(token)
    low = token.lower()
    if low in {"inf", "+inf", "-inf", "nan"}:
        return float(low)
    if not _NUMBER_RE.match(token):
        return None
    try:
        return float(token)
    except ValueError:
        return None


def parse_number(token: str) -> int | float | None:
    """Return an ``int`` when the token is integral, otherwise a ``float`` or ``None``."""
    value = parse_int(token)
    if value is not None:
        return value
    return parse_float(token)


def parse_duration(token: str) -> float | None:
    """``"524.50ms"`` -> ``0.5245`` seconds. Unit-less tokens are seconds."""
    match = _DURATION_RE.match(token.strip())
    if not match:
        return None
    return float(match.group("num")) * _DURATION_FACTORS[match.group("unit")]


def strip_row_name(token: str) -> str:
    """``"'core':"`` -> ``"core"``, ``"MIR_1:"`` -> ``"MIR_1"``."""
    token = token.strip()
    if token.endswith(":"):
        token = token[:-1]
    if len(token) >= 2 and token[0] == token[-1] == "'":
        token = token[1:-1]
    return token


def split_columns(text: str) -> list[str]:
    """Split a table line on runs of two or more spaces (CP-SAT's FormatTable spacing)."""
    text = text.strip()
    if not text:
        return []
    return re.split(r"\s{2,}", text)

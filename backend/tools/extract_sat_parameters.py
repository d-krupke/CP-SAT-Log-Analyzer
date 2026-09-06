"""Extract parameter documentation from OR-Tools' ``sat_parameters.proto``.

Created for the v2 analyzer so that the UI can explain every parameter a user
overrode (the ``Parameters:`` line of the log) with the authoritative comment
from the proto file, plus enum value docs, defaults and the section the
parameter belongs to.

Usage (run whenever a new OR-Tools version is out)::

    uv run python tools/extract_sat_parameters.py /path/to/or-tools/ortools/sat/sat_parameters.proto

Writes ``app/data/sat_parameters.json``:

    {"source": "...", "sections": [...],
     "parameters": {"num_workers": {"type": "int32", "default": "0", "doc": "...",
                                    "section": "...", "enum": null, "repeated": false}},
     "enums": {"SearchBranching": {"AUTOMATIC_SEARCH": "doc", ...}}}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FIELD = re.compile(
    r"^\s*(?P<label>optional|repeated|required)\s+(?P<type>[\w.]+)\s+(?P<name>\w+)\s*=\s*\d+"
    r"\s*(?:\[\s*default\s*=\s*(?P<default>[^\]]+?)\s*\])?\s*;"
)
ENUM_START = re.compile(r"^\s*enum\s+(?P<name>\w+)\s*\{")
ENUM_VALUE = re.compile(r"^\s*(?P<name>[A-Z][A-Z0-9_]*)\s*=\s*-?\d+\s*;")
COMMENT = re.compile(r"^\s*//\s?(?P<text>.*)$")
SECTION_RULE = re.compile(r"^\s*//\s*={10,}\s*$")


def extract(proto_text: str) -> dict:
    parameters: dict[str, dict] = {}
    enums: dict[str, dict[str, str]] = {}
    sections: list[str] = []
    section = "General"
    comments: list[str] = []
    pending_field: list[str] = []
    current_enum: str | None = None
    lines = proto_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if SECTION_RULE.match(line):
            # "// ====" / "// Title" / "// ====" header
            if (
                i + 1 < len(lines)
                and (m := COMMENT.match(lines[i]))
                and SECTION_RULE.match(lines[i + 1])
            ):
                section = m.group("text").strip()
                sections.append(section)
                i += 2
            comments = []
            continue
        if m := COMMENT.match(line):
            comments.append(m.group("text").rstrip())
            continue
        if not line.strip():
            comments = []
            continue
        if m := ENUM_START.match(line):
            current_enum = m.group("name")
            enums[current_enum] = {}
            comments = []
            continue
        if current_enum is not None:
            if line.strip().startswith("}"):
                current_enum = None
            elif m := ENUM_VALUE.match(line):
                enums[current_enum][m.group("name")] = _join(comments)
                comments = []
            continue
        pending_field.append(line.strip())
        joined = " ".join(pending_field)
        if ";" not in joined:
            continue
        pending_field = []
        if m := FIELD.match(joined):
            type_name = m.group("type")
            parameters[m.group("name")] = {
                "type": type_name,
                "repeated": m.group("label") == "repeated",
                "default": _clean_default(m.group("default")),
                "doc": _join(comments),
                "section": section,
                "enum": type_name if type_name in enums else None,
            }
        comments = []
    return {"sections": sections, "parameters": parameters, "enums": enums}


def _join(comments: list[str]) -> str:
    text = "\n".join(comments).strip()
    # collapse single newlines inside paragraphs, keep blank lines and list items
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para_lines = para.split("\n")
        if any(re.match(r"^\s*[-*]\s", pl) for pl in para_lines):
            out.append("\n".join(pl.rstrip() for pl in para_lines))
        else:
            out.append(" ".join(pl.strip() for pl in para_lines))
    return "\n\n".join(out)


def _clean_default(default: str | None) -> str | None:
    if default is None:
        return None
    default = default.strip()
    if default.startswith('"') and default.endswith('"'):
        return default[1:-1]
    return default


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    proto = Path(argv[1])
    data = extract(proto.read_text())
    data["source"] = f"ortools/sat/sat_parameters.proto ({proto.resolve()})"
    out = Path(__file__).resolve().parents[1] / "app" / "data" / "sat_parameters.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, sort_keys=True))
    print(f"wrote {len(data['parameters'])} parameters, {len(data['enums'])} enums to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

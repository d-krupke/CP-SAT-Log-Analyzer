import typing
from .tables import TableBlock

class LnsStatsBlock(TableBlock):

    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("LNS stats"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("LNS stats")
    
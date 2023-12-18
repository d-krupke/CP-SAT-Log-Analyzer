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
    
    def get_title(self) -> str:
        return "Large Neighborhood Search: Statistics"
    
    def get_help(self) -> typing.Optional[str]:
        return """
        This table gives you some statistics on the Large Neighborhood Search (LNS) strategies employed to find better solutions.

        If you are mainly interested in good solutions, you can use this information
        to determine which LNS strategies are most effective, and tell the solver to
        use more of those strategies in parallel.
"""

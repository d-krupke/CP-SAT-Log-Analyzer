import typing
from .tables import TableBlock


class SearchStatsBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("Search stats"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("Search stats")
    
    def get_title(self) -> str:
        return "Search Strategies: Statistics"
    
    def get_help(self) -> typing.Optional[str]:
        return """
        This table gives you some statistics on the different search strategies.
        How many variables where in the search space, how many conflicts were found, how many branches were executed, how often was the search restarted, and how often where the boolean and integer propagators applied.
"""

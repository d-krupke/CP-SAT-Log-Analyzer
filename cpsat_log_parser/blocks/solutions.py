import typing
from .tables import TableBlock
import re


class SolutionsBlock(TableBlock):
    """

    Not available for older versions of CP-SAT.
    """

    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not self.matches(lines):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    def get_num_solutions(self) -> int:
        # First line looks like this "Solutions (11)      Num    Rank"
        # We want to get the number in the parentheses
        return int(self.lines[0].split("(")[1].split(")")[0])

    def get_title(self) -> str:
        return "Solutions"

    def get_help(self) -> typing.Optional[str]:
        return """
        Which strategy found the most solutions?
        The rank indicates how good the found solutions are.
        Ranks with `[1,X]` indicate an optimal solution.
        """

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        # "Solutions (11)      Num    Rank"
        match = re.match(r"Solutions\s+\(\d+\)\s+Num\s+Rank", lines[0])
        return bool(match)

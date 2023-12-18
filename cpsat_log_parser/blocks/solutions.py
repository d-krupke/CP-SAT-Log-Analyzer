import typing
from .tables import TableBlock


class SolutionsBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("Solutions"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    def get_num_solutions(self) -> int:
        # First line looks like this "Solutions (11)      Num    Rank"
        # We want to get the number in the parentheses
        return int(self.lines[0].split("(")[1].split(")")[0])

    def get_title(self) -> str:
        return "Solutions"

    def get_help(self) -> str | None:
        return """
        Which strategy found the most solutions?
        The rank indicates how good the found solutions are.
        Ranks with `[1,X]` indicate an optimal solution.
        """

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("Solutions")

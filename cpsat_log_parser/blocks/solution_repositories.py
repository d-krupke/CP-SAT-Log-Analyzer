import typing
from .tables import TableBlock


class SolutionRepositoriesBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("Solution repositories"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        return lines[0].strip().startswith("Solution repositories") if lines else False

    def get_title(self) -> str:
        return "Solution Repositories"

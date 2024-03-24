import typing
from .tables import TableBlock


class ObjectiveBoundsBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("Objective bounds"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")

    def get_title(self) -> str:
        return "Objective bounds"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table gives an overview on which strategies improved the objective bounds. Together with the solutions table, this can be used to determine the most effective strategies. The less effective strategies can then be removed from the search, potentially freeing up resources for the more effective strategies.
        """

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        return lines[0].strip().startswith("Objective bounds") if lines else False

import typing
from .tables import TableBlock

class ObjectiveBoundsBlock(TableBlock):

    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)
        if not lines[0].startswith("Objective bounds"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")
        
    def get_title(self) -> str:
        return "Objective bounds"

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("Objective bounds")
    
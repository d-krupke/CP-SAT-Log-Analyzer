"""
This block can appear instead of the search progress block for pure satisfication models.
It does not seem to carry any additional information.

```
Starting sequential search at 0.01s
```
"""

from typing import List
import re
import typing
from .search_progress import SearchProgressBlock, parse_time

class SequentialSearchProgressBlock(SearchProgressBlock):
    def __init__(self, lines: List[str]) -> None:
        super().__init__(lines, check=False)

    @staticmethod
    def matches(lines: List[str]) -> bool:
        return len(lines) >= 1 and lines[0].startswith("Starting sequential search at")

    def get_presolve_time(self) -> float:
        if m := re.match(
            r"Starting sequential search at (?P<time>\d+\.\d+s)", self.lines[0]
        ):
            return parse_time(m["time"])
        raise ValueError(f"Could not parse presolve time from '{self.lines[0]}'")
    
    def get_help(self) -> typing.Optional[str]:
        return """
        This block indicates the start of the search phase. It is only present in satisfaction models and unfortunately gives not much information.

        You will get significantly more information in optimization models, in which case, this sections will actually contain some plots.
        """
    

"""

```
Clauses shared            Num
              'probing':    1
        'quick_restart':   15
  'quick_restart_no_lp':   14
```
"""

import typing
from .tables import TableBlock

class ClausesSharedBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Clauses shared")

    def get_title(self) -> str:
        return "Clauses Shared"

    def get_help(self) -> typing.Optional[str]:
        return None
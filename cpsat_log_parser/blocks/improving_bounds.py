"""

```
Improving bounds shared       Num
            'default_lp':     128
                'max_lp':  15'162
   'objective_lb_search':      74
               'probing':  13'411
        'probing_max_lp':   3'580
         'quick_restart':   3'739
         'reduced_costs':   2'798
```
"""

import typing
from .tables import TableBlock

class ImprovingBoundsSharedBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Improving bounds shared")

    def get_title(self) -> str:
        return "Improving Bounds Shared"

    def get_help(self) -> typing.Optional[str]:
        return None
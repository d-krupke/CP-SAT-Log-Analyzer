"""

```
Lp stats                      Component  Iterations  AddedCuts  OPTIMAL  DUAL_F.  DUAL_U.
               'default_lp':          1      30'297          0    6'951        2      125
                'fs_random':          1           0          0        0        3        0
                'fs_random':          1           0          0        0        3        0
  'fs_random_quick_restart':          1           0          0        0        3        0
           'lb_tree_search':          1       2'714      2'844       36       26        0
                   'max_lp':          1       4'567      2'157       48       39        0
      'objective_lb_search':          1      40'655          0    9'864        1      165
                  'probing':          1       8'268          0    5'237      255        0
           'probing_max_lp':          1       2'124      3'727       40        0        0
             'pseudo_costs':          1       2'191      4'240       47        0        0
            'quick_restart':          1      56'072          0    8'437        1       64
            'reduced_costs':          1       5'271      3'876       62      142       10
```
"""

from .tables import TableBlock
import typing


class LpStatsBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Lp stats")

    def get_title(self) -> str:
        return "Linear Programming: Statistics"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table shows statistics of the Linear Programming (LP) solver used in the
        different strategies.
        """

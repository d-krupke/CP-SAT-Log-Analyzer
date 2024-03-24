"""

```
Lp debug                      CutPropag  CutEqPropag  Adjust  Overflow      Bad  BadScaling
               'default_lp':          0            0   6'873         0        0           0
                'fs_random':          0            0       0         0        0           0
                'fs_random':          0            0       0         0        0           0
  'fs_random_quick_restart':          0            0       0         0        0           0
           'lb_tree_search':          0            0      61         0   85'173           0
                   'max_lp':          0            4      82         0  106'032           0
      'objective_lb_search':          0            0   4'734         0        0           0
                  'probing':          0            0   2'775         0        0           0
           'probing_max_lp':          0            2      39         0   89'095           0
             'pseudo_costs':          0            1      44         0  111'806           0
            'quick_restart':          0            0   7'002         0        0           0
            'reduced_costs':          0            0     210         0   92'579           0
```
"""

from .tables import TableBlock
import typing


class LpDebugBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        return lines[0].startswith("Lp debug") if lines else False

    def get_title(self) -> str:
        return "Linear Programming: Debug Information"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table shows debug information of the Linear Programming (LP) solver used in the
        different strategies. Not relevant for most users.
        """

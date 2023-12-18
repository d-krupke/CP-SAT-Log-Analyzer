"""

```
Lp dimension                                                                        Final dimension of first component
               'default_lp':     399 rows, 39800 columns, 63670 entries with magnitude in [1.000000e+00, 1.000000e+00]
                'fs_random':           0 rows, 39800 columns, 0 entries with magnitude in [0.000000e+00, 0.000000e+00]
                'fs_random':           0 rows, 39800 columns, 0 entries with magnitude in [0.000000e+00, 0.000000e+00]
  'fs_random_quick_restart':           0 rows, 39800 columns, 0 entries with magnitude in [0.000000e+00, 0.000000e+00]
           'lb_tree_search':   959 rows, 39800 columns, 1322620 entries with magnitude in [3.265715e-05, 1.000000e+00]
                   'max_lp':     992 rows, 39800 columns, 60616 entries with magnitude in [2.102000e-05, 1.000000e+00]
      'objective_lb_search':     399 rows, 39800 columns, 44821 entries with magnitude in [1.000000e+00, 1.000000e+00]
                  'probing':     396 rows, 39800 columns, 18798 entries with magnitude in [1.000000e+00, 1.000000e+00]
           'probing_max_lp':  1030 rows, 39800 columns, 1253075 entries with magnitude in [5.237120e-05, 1.000000e+00]
             'pseudo_costs':  1106 rows, 39800 columns, 1873488 entries with magnitude in [4.676762e-05, 1.000000e+00]
            'quick_restart':     399 rows, 39800 columns, 18892 entries with magnitude in [1.000000e+00, 1.000000e+00]
            'reduced_costs':  1150 rows, 39800 columns, 1854299 entries with magnitude in [1.492784e-05, 1.000000e+00]
```
"""

from .tables import TableBlock
import typing

class LpDimensionBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Lp dimension")

    def get_title(self) -> str:
        return "Linear Programming: Dimensions"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table shows the dimensions of the linear programs used in the different strategies. This information is not relevant for most users.
        """
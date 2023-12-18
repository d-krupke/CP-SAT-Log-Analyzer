"""

```
Lp pool                       Constraints  Updates  Simplif  Merged  Shortened  Split  Strenghtened    Cuts/Call
               'default_lp':          400        0      557     400        557      0             0          0/0
                'fs_random':          400        0        0     400          0      0             0          0/0
                'fs_random':          400        0        0     400          0      0             0          0/0
  'fs_random_quick_restart':          400        0        0     400          0      0             0          0/0
           'lb_tree_search':        3'244    2'559   23'009     400     24'642      2           137  2'844/4'301
                   'max_lp':        2'557    2'677   19'764     400     20'670     24           208  2'157/4'077
      'objective_lb_search':          400        0    1'771     400      1'771      0             0          0/0
                  'probing':          400        0   18'185     400     18'185      0             0          0/0
           'probing_max_lp':        4'127    1'999    7'261     400      8'648      2           408  3'727/5'263
             'pseudo_costs':        4'640    2'255   40'614     400     42'301      5         1'395  4'240/5'963
            'quick_restart':          400        0   12'414     400     12'414      0             0          0/0
            'reduced_costs':        4'276    2'340   35'142     400     37'466      2         1'225  3'876/6'793
```
"""

from .tables import TableBlock
import typing

class LpPoolBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Lp pool")

    def get_title(self) -> str:
        return "Linear Programming: Pool"

    def get_help(self) -> typing.Optional[str]:
        return None  # TODO
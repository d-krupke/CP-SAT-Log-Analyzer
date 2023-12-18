"""

```
LS stats                   Batches  Restarts  LinMoves  GenMoves  CompoundMoves  WeightUpdates
       'fj_long_default':        1         1       200        38              0              6
   'fj_long_lin_default':        1         1         0       292            199              0
      'fj_short_default':        1         1         0       302            199              0
  'fj_short_lin_default':        1         1         0       210            206              0
          'violation_ls':       10         0       987     1'094              0            303
          'violation_ls':       12         0     6'820     1'118              2         23'755


```
"""

from .tables import TableBlock
import typing


class LsStatsBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("LS stats")

    def get_title(self) -> str:
        return "Local Search: Statistics"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table shows statistics of the local search strategies.
        """

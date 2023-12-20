"""
```
Preloading model.
#Bound   3.52s best:inf   next:[44854518,1.3115287e+12] initial_domain
[Symmetry] Graph for symmetry has 159'002 nodes and 316'608 arcs.
[Symmetry] Symmetry computation done. time: 0.0122073 dtime: 0.0401119
#Model   3.57s var:39999/39999 constraints:79403/79403
```
"""

from .log_block import LogBlock
import typing


class PreloadingModelBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Preloading model.")

    def get_title(self) -> str:
        return "Preloading Model"

    def get_help(self) -> str:
        return """This block is a prelude to the search phase and gives an overview of the model at the start of the search phase.
        """
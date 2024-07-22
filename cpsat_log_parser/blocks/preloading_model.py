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
        return lines[0].startswith("Preloading model.") if lines else False

    def get_title(self) -> str:
        return "Preloading Model"

    def get_help(self) -> str:
        return """This block serves as a prelude to the search phase and provides an overview of the model at the beginning of the search. Typically, this information is not very interesting unless the presolve phase was highly effective, essentially solving the model before the search phase begins. This can lead to entries that look very similar to that of the actual search phase, which comes next.
        """

"""
```
Lp Cut             max_lp  reduced_costs  pseudo_costs  lb_tree_search  probing_max_lp
           CG_FF:     374            718           770             680             854
            CG_K:     121            315           262             333             318
           CG_KL:       -              -             1               -               -
            CG_R:   1'109          2'454         2'807           1'309           2'073
         Circuit:     210            256           201             203             206
  CircuitBlossom:      18             10            15              16               -
    CircuitExact:       1              1             1               1               -
          Clique:      31             35            33              31              37
        MIR_1_FF:       -              -             1               -               -
         MIR_1_R:      14              3             6               7               2
        MIR_2_FF:       -              1             -               -               1
         MIR_2_R:      76             16            29              66              42
        MIR_3_FF:       1              -             -               -               -
         MIR_3_R:      56             13            18              44              45
        MIR_4_FF:       1              -             -               -               1
         MIR_4_R:      39             14            17              45              37
        MIR_5_FF:      35             22            32              33              24
         MIR_5_R:      26              2             9              45              24
        MIR_6_FF:      14              6            11               8               4
         MIR_6_R:      15              6             5              22              16
    ZERO_HALF_FF:       7              3            12               1              34
     ZERO_HALF_R:       9              1            10               -               9
```
"""

from .tables import TableBlock
import typing


class LpCutBlock(TableBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Lp Cut")

    def get_title(self) -> str:
        return "Linear Programming: Cutting Planes"

    def get_help(self) -> typing.Optional[str]:
        return """
        This table shows the number of different cutting planes added to the LP solver
        in different strategies. The cutting planes are used to strengthen the LP relaxation
        of the problem and are a key ingredient of state-of-the-art branch-and-cut solvers.
        """

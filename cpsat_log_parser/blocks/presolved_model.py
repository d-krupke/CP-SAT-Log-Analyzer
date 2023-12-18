"""

Presolved optimization model '': (model_fingerprint: 0x301e2e572c48f057)
#Variables: 243'301 (#bools: 243'301 in objective)
  - 243'301 Booleans in [0,1]
#kAtMostOne: 2'000 (#literals: 486'602)
#kLinearN: 1'000 (#terms: 486'602)

"""

from .log_block import LogBlock
import typing


class PresolvedModelBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Presolved optimization model")

    def get_title(self) -> str:
        return "Presolved Optimization Model"

    def get_model_fingerprint(self) -> str:
        return self.lines[0].split("model_fingerprint: ")[1].strip(")")

    def get_num_variables(self) -> int:
        return int(
            self.lines[1]
            .split("#Variables: ")[1]
            .strip()
            .split(" ")[0]
            .replace("'", "")
        )

    def get_num_constraints(self) -> int:
        n = 0
        for line in self.lines:
            if line.startswith("#k"):
                # "#kNoOverlap2D: 1 (#rectangles: 24)"
                # "#kInterval: 48"
                n += int(line.split(":")[1].strip().split(" ")[0].replace("'", ""))
        return n

    def get_help(self) -> str | None:
        return """
        This is the most important block of the presolve phase and gives an overview of the model after presolve.
        It contains the number of variables and constraints, as well as coefficients and domains.

        It is useful to compare this to the initial model, to see if your
        model was simplified by presolve, which indicates that you can
        simplify your model yourself, saving presolve time.

        It is also interesting to see if the presolve replaced some of your
        constraints with more efficient ones.
        """

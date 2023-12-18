"""

This block can look like this:

Initial optimization model '': (model_fingerprint: 0x68818998b4c0a611)
#Variables: 245'237 (#bools: 245'237 in objective)
  - 245'237 Booleans in [0,1]
#kLinearN: 3'000 (#terms: 980'948)

or like this:

Initial satisfaction model '': (model_fingerprint: 0x26124a74348f784d)
#Variables: 48
  - 3 in [0,100]
  - 6 in [0,110]
  - 6 in [0,120]
  - 9 in [0,130]
  - 4 in [0,270]
  - 2 in [0,280]
  - 5 in [0,290]
  - 2 in [0,310]
  - 2 in [0,330]
  - 1 in [0,340]
  - 2 in [0,350]
  - 2 in [0,370]
  - 2 in [0,380]
  - 2 in [0,390]
#kInterval: 48
#kLinear1: 48
#kNoOverlap2D: 1 (#rectangles: 24)
"""

from .log_block import LogBlock
import typing


class InitialModelBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Initial optimization model")

    def get_title(self) -> str:
        return "Initial Optimization Model"

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

    def get_help(self) -> typing.Optional[str]:
        return """
        This block gives an overview of the model before presolve.
        It contains the number of variables and constraints, as well as coefficients and domains.
        """

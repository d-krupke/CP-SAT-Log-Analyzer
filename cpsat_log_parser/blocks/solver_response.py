from .log_block import LogBlock
import typing
import pandas as pd


class ResponseBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("CpSolverResponse")

    def get_title(self) -> str:
        return "CpSolverResponse"

    def to_dict(self) -> dict:
        d = {}
        for line in self.lines:
            if line.startswith("CpSolverResponse"):
                continue
            key, value = line.split(":")
            key = key.strip()
            value = value.strip()
            if key == "status":
                value = value.split(" ")[0]
            d[key] = value
        return d

    def get_gap(self):
        vals = self.to_dict()
        try:
            obj = int(vals["objective"])
            bound = int(vals["best_bound"])
        except TypeError:
            return None
        return 100*(abs(obj - bound) / max(1, abs(obj)))

    def to_pandas(self) -> pd.DataFrame:
        return pd.DataFrame([self.to_dict()])

    def get_help(self) -> typing.Optional[str]:
        return """
        This final block of the log contains a summary by the solver.
        Here you find the most important information, such as how successful the search was.

        You can find the original documentation [here](https://github.com/google/or-tools/blob/8768ed7a43f8899848effb71295a790f3ecbe2f2/ortools/sat/cp_model.proto#L720).
        """

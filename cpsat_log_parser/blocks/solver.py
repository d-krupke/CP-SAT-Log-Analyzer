"""
The solver block is the first part of the log.
"""


from .log_block import LogBlock
import typing
import re


class SolverBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    def _parse_parameters(self, line: str) -> typing.Dict:
        """
        The parameters line can look like this:
        "Parameters: log_search_progress: true use_timetabling_in_no_overlap_2d: true use_energetic_reasoning_in_no_overlap_2d: true use_pairwise_reasoning_in_no_overlap_2d: true"
        """
        line = line[len("Parameters:") :]
        return {
            match.group("key"): match.group("value")
            for match in re.finditer(r"(?P<key>\w+): (?P<value>[^ ]+)", line)
        }

    def get_title(self) -> str:
        return "Solver Information"

    def get_help(self) -> str:
        return """This block contains basic information about the solver.
        As CP-SAT is still under active development and makes serious improvements with every release, it is important to know which version of the solver was used.
        The number of workers, i.e., the level of parallelism, is also important to know.
        CP-SAT is a portfolio solver and the higher the number of workers, the more strategies are used.
        You can find an overview of the different tiers activated by the number of workers in the [CP-SAT documentation](https://github.com/google/or-tools/blob/main/ortools/sat/docs/troubleshooting.md#improving-performance-with-multiple-workers).
        While you should be careful with tinkering with the parameters (they have sensible defaults), it is still good to know which parameters were used.
        All of these information are actually already shown in the overview.
        """

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("Starting CP-SAT solver")

    def get_parameters(self) -> typing.Dict:
        for line in self.lines:
            if line.startswith("Parameters:"):
                return self._parse_parameters(line)
        raise ValueError("No parameters found")

    def get_number_of_workers(self) -> int:
        # the line looks like this: "Setting number of workers to 24"
        for line in self.lines:
            if line.startswith("Setting number of workers to"):
                return int(line.strip().split(" ")[-1])
        # If `num_workers` is set, the number of workers is not shown in the log.
        if "num_workers" in self.get_parameters():
            return int(self.get_parameters()["num_workers"])
        # `num_search_workers` is deprecated in favor `num_workers`, but if the
        # latter is not set, `num_search_workers` is still used.
        if "num_search_workers" in self.get_parameters():
            return int(self.get_parameters()["num_search_workers"])
        raise ValueError("No number of workers found")

    def get_version(self) -> str:
        # the line looks like this: "Starting CP-SAT solver v9.7.2996"
        for line in self.lines:
            if line.startswith("Starting CP-SAT solver"):
                return line.strip().split(" ")[-1]
        raise ValueError("No version found")

    def get_parsed_version(self) -> typing.Tuple[int, int, int]:
        # the line looks like this: "Starting CP-SAT solver v9.7.2996"
        version = self.get_version()[1:]
        major, minor, patch = version.split(".")
        return int(major), int(minor), int(patch)

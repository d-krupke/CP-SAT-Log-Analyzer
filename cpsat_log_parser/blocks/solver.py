"""
The solver block is the first part of the log.
"""


from .log_block import LogBlock
import typing
import re

import re

def _convert_value(value):
    """Convert the token value to its appropriate type."""
    if isinstance(value, list):
        return [_convert_value(v) for v in value]
    if isinstance(value, dict):
        return value
    if value.startswith('"') and value.endswith('"'):
        return value.strip('"')  # Strip quotes if it's a quoted string
    elif value == 'true':
        return True
    elif value == 'false':
        return False
    elif value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value  # If it cannot be converted to a number, keep as is


def _parse_block(tokens) -> dict:
    block_dict = {}
    while tokens:
        key = tokens.pop(0)
        if key == '}':
            return block_dict
        value = tokens.pop(0)
        if value == '{':
            value = _parse_block(tokens)
        value = _convert_value(value)
        if key in block_dict:
            if not isinstance(block_dict[key], list):
                block_dict[key] = [block_dict[key]]
            block_dict[key].append(value)
        else:
            block_dict[key] = value
    return block_dict

def parse_parameters_line(line: str) -> dict[str, str|int|float|bool|list|dict]:
    """Parse the 'Parameters: ' line and return a dictionary of parameters."""
    if not line.startswith('Parameters: '):
        raise ValueError('The line must begin with "Parameters: "')
    
    tokens = re.split(r' (?=(?:[^"]*"[^"]*")*[^"]*$)', line)
    tokens.pop(0)  # remove "Parameters:" token

    return _parse_block(tokens)


class SolverBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    def _parse_parameters(self, line: str) -> typing.Dict:
        """
        The parameters line can look like this:
        "Parameters: log_search_progress: true use_timetabling_in_no_overlap_2d: true use_energetic_reasoning_in_no_overlap_2d: true use_pairwise_reasoning_in_no_overlap_2d: true"
        """
        return parse_parameters_line(line)

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

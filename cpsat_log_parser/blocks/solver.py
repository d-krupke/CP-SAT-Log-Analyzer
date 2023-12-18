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
        parameters = {}
        line = line[len("Parameters:"):]
        for match in re.finditer(r"(?P<key>\w+): (?P<value>\w+)", line):
            parameters[match.group("key")] = match.group("value")
        return parameters
    
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

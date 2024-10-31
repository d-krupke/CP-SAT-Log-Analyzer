"""

```
Presolve summary:
  - 0 affine relations were detected.
  - rule 'deductions: 79003 stored' was applied 1 time.
  - rule 'exactly_one: simplified objective' was applied 264 times.
  - rule 'incompatible linear: add implication' was applied 59'103 times.
  - rule 'linear: empty' was applied 1 time.
  - rule 'linear: fixed or dup variables' was applied 200 times.
  - rule 'linear: reduced variable domains' was applied 1 time.
  - rule 'objective: shifted cost with exactly ones' was applied 228 times.
  - rule 'presolve: 1 unused variables removed.' was applied 1 time.
  - rule 'presolve: iteration' was applied 3 times.
  - rule 'variables: detect half reified value encoding' was applied 199 times.
```
"""

from .log_block import LogBlock
import typing


class PresolveSummaryBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        return lines[0].strip().startswith("Presolve summary:") if lines else False

    def get_title(self) -> str:
        return "Presolve Summary"

    def get_help(self) -> str:
        return """This block gives an overview of the presolve phase and how often which rule was applied."""

    def is_solved_by_presolve(self) -> bool:
        return any("Problem closed by presolve." in line for line in self.lines)

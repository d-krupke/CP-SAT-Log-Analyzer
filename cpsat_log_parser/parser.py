import typing
from .blocks import (
    LogBlock,
    SearchProgressBlock,
    SearchStatsBlock,
    LnsStatsBlock,
    SolutionRepositoriesBlock,
    SolutionsBlock,
    ObjectiveBoundsBlock,
    SolverBlock,
    ResponseBlock,
    PresolveLogBlock,
    InitialModelBlock,
)


def _split_log(
    log: typing.Union[typing.List[str], str]
) -> typing.List[typing.List[str]]:
    """
    Split the log into its elements. Two elements are separated by a blank line.
    """
    if isinstance(log, str):
        log = log.split("\n")
    if not isinstance(log, list):
        raise TypeError("log must be a list or a string")
    # split into elements
    elements = []
    current_element = []
    for line in log:
        line = line.rstrip()
        if not line:
            # empty line, start a new element
            if current_element:
                elements.append(current_element)
            current_element = []
        else:
            current_element.append(line)
    if current_element:
        elements.append(current_element)
    return elements


def parse_blocks(log: typing.Union[str, typing.List[str]]) -> typing.List[LogBlock]:
    """
    Parse a log into its blocks.
    """
    blocks = []
    for data in _split_log(log):
        if SolverBlock.matches(data):
            blocks.append(SolverBlock(data))
        elif SearchProgressBlock.matches(data):
            blocks.append(SearchProgressBlock(data))
        elif SearchStatsBlock.matches(data):
            blocks.append(SearchStatsBlock(data))
        elif LnsStatsBlock.matches(data):
            blocks.append(LnsStatsBlock(data))
        elif SolutionRepositoriesBlock.matches(data):
            blocks.append(SolutionRepositoriesBlock(data))
        elif SolutionsBlock.matches(data):
            blocks.append(SolutionsBlock(data))
        elif ResponseBlock.matches(data):
            blocks.append(ResponseBlock(data))
        elif ObjectiveBoundsBlock.matches(data):
            blocks.append(ObjectiveBoundsBlock(data))
        elif PresolveLogBlock.matches(data):
            blocks.append(PresolveLogBlock(data))
        elif InitialModelBlock.matches(data):
            blocks.append(InitialModelBlock(data))
        else:
            blocks.append(LogBlock(data))
    return blocks

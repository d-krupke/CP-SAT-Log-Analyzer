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
    PresolvedModelBlock,
    LpStatsBlock,
    LpDebugBlock,
    LpDimensionBlock,
    LpPoolBlock,
    LpCutBlock,
    ImprovingBoundsSharedBlock,
    ClausesSharedBlock,
    LsStatsBlock,
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
    sub_parser = [
        SolverBlock,
        SearchProgressBlock,
        SearchStatsBlock,
        LnsStatsBlock,
        SolutionRepositoriesBlock,
        SolutionsBlock,
        ResponseBlock,
        ObjectiveBoundsBlock,
        PresolveLogBlock,
        InitialModelBlock,
        PresolvedModelBlock,
        LpStatsBlock,
        LpDebugBlock,
        LpDimensionBlock,
        LpPoolBlock,
        LpCutBlock,
        LsStatsBlock,
        ImprovingBoundsSharedBlock,
        ClausesSharedBlock,
        LogBlock
    ]
    for data in _split_log(log):
        for parser in sub_parser:
            if parser.matches(data):
                blocks.append(parser(data))
                break
        else:
            raise ValueError(f"Could not parse data: {data}")
    return blocks

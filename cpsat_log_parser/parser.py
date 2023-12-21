import typing
from .blocks import ALL_BLOCKS, LogBlock


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
    sub_parser = ALL_BLOCKS
    for data in _split_log(log):
        for parser in sub_parser:
            if parser.matches(data):
                blocks.append(parser(data))
                break
        else:
            raise ValueError(f"Could not parse data: {data}")
    return blocks


class LogParser:
    def __init__(self, log: typing.Union[str, typing.List[str]]) -> None:
        self.comments, log_without_comments = self._extract_comments(log)
        self.blocks = self.parse_blocks(log_without_comments)

    def parse_blocks(
        self, log: typing.Union[str, typing.List[str]]
    ) -> typing.List[LogBlock]:
        """
        Parse a log into its blocks.
        """
        blocks = []
        sub_parser = ALL_BLOCKS
        for data in _split_log(log):
            for parser in sub_parser:
                if parser.matches(data):
                    blocks.append(parser(data))
                    break
            else:
                raise ValueError(f"Could not parse data: {data}")
        return blocks

    def _extract_comments(
        self, log: typing.Union[str, typing.List[str]]
    ) -> typing.Tuple[typing.List[str], typing.List[str]]:
        """
        Extract the comments from a log.
        """
        if isinstance(log, str):
            log = log.split("\n")
        if not isinstance(log, list):
            raise TypeError("log must be a list or a string")
        comments = []
        data = []
        for line in log:
            if line.startswith("//"):
                comments.append(line[2:].strip())
            else:
                data.append(line)
        return comments, data

    def get_block_of_type(
        self, block_type: typing.Type[LogBlock]
    ) -> typing.Optional[LogBlock]:
        for block in self.blocks:
            if isinstance(block, block_type):
                return block
        return None

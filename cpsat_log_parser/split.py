import typing

def split_log(log: typing.Union[typing.List[str], str]) -> typing.List[typing.List[str]]:
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

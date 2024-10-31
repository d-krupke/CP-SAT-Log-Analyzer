"""
A generic table block that can parse most tables in the log.
"""

import typing
import re
import pandas as pd
from io import StringIO
from .log_block import LogBlock


class TableBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        if not lines:
            raise ValueError("No lines to parse")
        self.lines = lines
        self._df = None

    def to_pandas(self) -> pd.DataFrame:
        """
        Parse the table into a pandas DataFrame.
        """
        log = "\n".join((line.strip() for line in self.lines))
        # Replace the single quotes with nothing
        log = log.replace("'", "")

        # Replace two or more spaces with a single tab
        log = re.sub(r"\s\s+", "\t", log)

        # Use StringIO to convert the string to a file-like object for read_csv
        log_file = StringIO(log)

        df = pd.read_csv(log_file, delimiter="\t", index_col=0)
        return df

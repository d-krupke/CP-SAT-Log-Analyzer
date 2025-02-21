import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cpsat_log_parser import LogParser
from cpsat_log_parser.blocks import (
    SearchProgressBlock,
    SequentialSearchProgressBlock,
    SolverBlock,
    ResponseBlock,
    PresolveSummaryBlock
)

EXAMPLE_DIR = os.path.join(os.path.dirname(__file__), "../example_logs")


def test_all_examples():
    for file in os.listdir(EXAMPLE_DIR):
        if file.endswith(".txt"):
            with open(os.path.join(EXAMPLE_DIR, file)) as f:
                print(f"Testing {file}")
                data = f.read()
                parser = LogParser(data)
                parser.get_block_of_type(SolverBlock).get_parameters()
                try:
                    parser.get_block_of_type(SearchProgressBlock)
                except KeyError:
                    if parser.get_block_of_type(PresolveSummaryBlock).is_solved_by_presolve():
                        continue
                    parser.get_block_of_type(SequentialSearchProgressBlock)
                parser.get_block_of_type(ResponseBlock)

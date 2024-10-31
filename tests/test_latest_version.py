import random
from ortools.sat.python import cp_model  # pip install -U ortools
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cpsat_log_parser import LogParser
from cpsat_log_parser.blocks import (
    SearchProgressBlock,
    SequentialSearchProgressBlock,
    SolverBlock,
    ResponseBlock,
)


def test_latest_cpsat():
    # Specifying the input
    n = 5_000
    weights = [random.randint(1, 1000) for _ in range(n)]
    values = [random.randint(1, 100) for _ in range(n)]
    capacity = 20 * n

    # Now we solve the problem
    model = cp_model.CpModel()
    xs = [model.new_bool_var(f"x_{i}") for i in range(len(weights))]

    model.add(sum(x * w for x, w in zip(xs, weights)) <= capacity)
    model.maximize(sum(x * v for x, v in zip(xs, values)))

    solver = cp_model.CpSolver()
    log = []
    solver.parameters.log_search_progress = True
    solver.log_callback = lambda line: log.append(line)
    solver.solve(model)
    print("\n".join(log))
    parser = LogParser("\n".join(log))
    parser.get_block_of_type(SolverBlock).get_parameters()
    try:
        parser.get_block_of_type(SearchProgressBlock)
    except KeyError:
        parser.get_block_of_type(SequentialSearchProgressBlock)
    parser.get_block_of_type(ResponseBlock)

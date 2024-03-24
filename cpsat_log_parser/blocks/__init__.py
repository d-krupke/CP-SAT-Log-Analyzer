"""
This folder contains the logic for parsing individual blocks from the log.
"""

from .search_progress import SearchProgressBlock
from .search_stats import SearchStatsBlock
from .lns_stats import LnsStatsBlock
from .solution_repositories import SolutionRepositoriesBlock
from .solutions import SolutionsBlock
from .objective_bounds import ObjectiveBoundsBlock
from .log_block import LogBlock
from .tables import TableBlock
from .solver import SolverBlock
from .solver_response import ResponseBlock
from .presolve_log import PresolveLogBlock
from .initial_model import InitialModelBlock
from .presolved_model import PresolvedModelBlock
from .lp_stats import LpStatsBlock
from .lp_debug import LpDebugBlock
from .lp_dimension import LpDimensionBlock
from .lp_pool import LpPoolBlock
from .lp_cut import LpCutBlock
from .ls_stats import LsStatsBlock
from .improving_bounds import ImprovingBoundsSharedBlock
from .clauses_shared import ClausesSharedBlock
from .task_timing import TaskTimingBlock
from .presolve_summary import PresolveSummaryBlock
from .preloading_model import PreloadingModelBlock
from .sequential_search_progress import SequentialSearchProgressBlock

# The order of the following list is important.
# The first matching block is used.
ALL_BLOCKS = [
    SearchProgressBlock,
        SequentialSearchProgressBlock,
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
    LsStatsBlock,
    ImprovingBoundsSharedBlock,
    ClausesSharedBlock,
    TaskTimingBlock,
    PreloadingModelBlock,
    PresolveSummaryBlock,
    #TableBlock,  # Seems to be problematic
    LogBlock,
]

__all__ = list(ALL_BLOCKS)

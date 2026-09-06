#!/usr/bin/env bash
# Collect the full benchmark log corpus (created 2026-09-06).
#
# Five batches, each resumable (existing logs are skipped unless --force):
#   A baseline   every problem, 8 workers, 60 s, 6 instances spread over the sizes
#   B 1 worker   the single `main` worker portfolio (no parallel subsolvers)
#   C 24 workers full portfolio incl. shared-tree workers on this 24-core machine
#   D parameter variants (no LP, no presolve, LNS only, interleaved, enumeration)
#   E MiniZinc Challenge families through the bundled MiniZinc + cp-sat backend
#
# Usage: ./collect_all.sh [batch letters, default ABCDE]
set -uo pipefail
cd "$(dirname "$0")"
BATCHES="${*:-ABCDE}"
SUBSET="tsp jobshop rcpsp qap set_covering graph_coloring mknapsack strip_packing cvrp sudoku"
run() { echo; echo "=== $* ==="; uv run python "$@"; }

[[ $BATCHES == *A* ]] && run run.py solve --limit 60 --workers 8 --max-instances 6
[[ $BATCHES == *B* ]] && run run.py solve $SUBSET --limit 30 --workers 1 --max-instances 3
[[ $BATCHES == *C* ]] && run run.py solve $SUBSET --limit 30 --workers 24 --max-instances 3
if [[ $BATCHES == *D* ]]; then
  run run.py solve tsp jobshop qap --limit 30 --workers 8 --max-instances 2 \
      --param linearization_level=0 --tag nolp
  run run.py solve set_covering mknapsack rcpsp --limit 30 --workers 8 --max-instances 2 \
      --param cp_model_presolve=false --tag nopresolve
  run run.py solve qap set_covering strip_packing --limit 30 --workers 8 --max-instances 2 \
      --param use_lns_only=true --tag lnsonly
  run run.py solve jobshop graph_coloring cvrp --limit 30 --workers 8 --max-instances 2 \
      --param interleave_search=true --tag interleave
  run run.py solve sudoku langford --limit 10 --workers 8 --max-instances 1 \
      --param enumerate_all_solutions=true --tag enumall
fi
[[ $BATCHES == *E* ]] && run mzn_run.py solve --limit 60 --workers 8 --max-instances 2
echo; echo "=== done: $(find logs -name '*.txt' | wc -l) logs ==="

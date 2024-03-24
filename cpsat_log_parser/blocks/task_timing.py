"""

```
Task timing                          n [     min,      max]      avg      dev     time         n [     min,      max]      avg      dev    dtime
                     'core':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [  21.32s,   21.32s]   21.32s   0.00ns   21.32s
               'default_lp':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   1.89s,    1.89s]    1.89s   0.00ns    1.89s
         'feasibility_pump':        37 [ 26.79ms,  55.33ms]  32.14ms   5.46ms    1.19s        36 [  1.55ms,   9.11ms]   3.10ms   1.11ms 111.43ms
          'fj_long_default':         0 [  0.00ns,   0.00ns]   0.00ns   0.00ns   0.00ns         0 [  0.00ns,   0.00ns]   0.00ns   0.00ns   0.00ns
         'fj_short_default':         1 [  8.46ms,   8.46ms]   8.46ms   0.00ns   8.46ms         0 [  0.00ns,   0.00ns]   0.00ns   0.00ns   0.00ns
                'fs_random':         1 [ 37.98ms,  37.98ms]  37.98ms   0.00ns  37.98ms         1 [ 20.00ns,  20.00ns]  20.00ns   0.00ns  20.00ns
  'fs_random_quick_restart':         1 [ 39.50ms,  39.50ms]  39.50ms   0.00ns  39.50ms         1 [ 20.00ns,  20.00ns]  20.00ns   0.00ns  20.00ns
            'graph_arc_lns':        36 [ 25.44ms,    1.04s] 190.28ms 193.39ms    6.85s        36 [ 34.00ns, 100.42ms]  55.06ms  45.86ms    1.98s
            'graph_cst_lns':        36 [ 14.90ms, 623.70ms] 152.40ms 132.41ms    5.49s        36 [ 10.00ns, 103.95ms]  56.24ms  46.94ms    2.02s
            'graph_dec_lns':        36 [ 23.06ms, 817.06ms] 198.86ms 167.04ms    7.16s        36 [ 10.00ns, 101.18ms]  53.20ms  47.63ms    1.92s
            'graph_var_lns':        36 [ 29.88ms, 940.02ms] 163.00ms 178.31ms    5.87s        36 [377.00ns, 100.34ms]  55.69ms  47.44ms    2.00s
           'lb_tree_search':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   5.20s,    5.20s]    5.20s   0.00ns    5.20s
                   'max_lp':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   1.92s,    1.92s]    1.92s   0.00ns    1.92s
                    'no_lp':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   1.65s,    1.65s]    1.65s   0.00ns    1.65s
      'objective_lb_search':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   2.50s,    2.50s]    2.50s   0.00ns    2.50s
                  'probing':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [370.46ms, 370.46ms] 370.46ms   0.00ns 370.46ms
             'pseudo_costs':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   1.68s,    1.68s]    1.68s   0.00ns    1.68s
            'quick_restart':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   2.33s,    2.33s]    2.33s   0.00ns    2.33s
      'quick_restart_no_lp':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   3.44s,    3.44s]    3.44s   0.00ns    3.44s
            'reduced_costs':         1 [  12.47s,   12.47s]   12.47s   0.00ns   12.47s         1 [   1.65s,    1.65s]    1.65s   0.00ns    1.65s
                'rins/rens':        36 [  4.49ms,    1.06s] 291.32ms 290.78ms   10.49s        33 [ 10.00ns, 100.11ms]  65.50ms  46.71ms    2.16s
              'rnd_cst_lns':        36 [ 19.64ms,    1.00s] 165.27ms 184.01ms    5.95s        36 [ 10.00ns, 101.61ms]  59.23ms  46.79ms    2.13s
              'rnd_var_lns':        36 [ 32.02ms,    1.09s] 216.37ms 223.53ms    7.79s        36 [332.00ns, 100.46ms]  56.08ms  47.00ms    2.02s
             'violation_ls':        36 [  5.49ms,    3.32s] 315.06ms 519.71ms   11.34s        36 [ 93.43us, 857.12ms]  74.01ms 135.75ms    2.66s

Search Strategies: Statistics

```
"""

import typing
from typing import List
import pandas as pd
import re
from io import StringIO
from .log_block import LogBlock


class TaskTimingBlock(LogBlock):
    def __init__(self, lines: List[str]) -> None:
        super().__init__(lines)
        if not self.matches(lines):
            raise ValueError("Invalid lines for TaskTimingBlock")

    @staticmethod
    def matches(lines: List[str]) -> bool:
        if not lines:
            return False
        return lines[0].startswith("Task timing")

    def get_help(self) -> typing.Optional[str]:
        return "The time spent on each subsolver. Does not give much useful information for the common user."

    def get_title(self) -> str:
        return "Task Timing"

    def to_pandas(self, deterministic: bool) -> pd.DataFrame:
        lines = [line.strip() for line in self.lines if line.strip()]
        lines = [line.replace("'", "") for line in lines]
        lines = [line.replace("[", "  ") for line in lines]
        lines = [line.replace("]", "  ") for line in lines]
        lines = [line.replace(",", "  ") for line in lines]
        lines = [line.replace("\t", "  ") for line in lines]
        lines = [line.replace("s ", "s  ") for line in lines]
        lines = [re.sub(r"\s\s+", "\t", line) for line in lines]

        def filter(line):
            split_line = line.split("\t")
            n = len(split_line)
            if deterministic:
                return "\t".join(split_line[:1] + split_line[n // 2 + 1 :])
            else:
                return "\t".join(split_line[: n // 2 + 1])

        lines = [filter(line) for line in lines]
        if deterministic:
            lines[0] = lines[0].replace("Task timing", "Task timing (deterministic)")

        # Replace two or more spaces with a single tab
        log = "\n".join(lines)
        log = re.sub(r"\s\s+", "\t", log)

        # Use StringIO to convert the string to a file-like object for read_csv
        log_file = StringIO(log)

        df = pd.read_csv(log_file, delimiter="\t", index_col=0)
        return df

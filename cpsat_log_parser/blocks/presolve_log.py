"""
A presolve log can look like this:

Starting presolve at 0.03s
[ExtractEncodingFromLinear] #potential_supersets=2000 #potential_subsets=0 #at_most_one_encodings=0 #exactly_one_encodings=0 #unique_terms=0 #multiple_terms=0 #literals=0 time=0.00628924s
[Symmetry] Graph for symmetry has 492416 nodes and 1225127 arcs.
[Symmetry] GraphSymmetryFinder error: Some automorphisms were found, but probably not all.
[Symmetry] Symmetry computation done. time: 0.83449 dtime: 1.00012
[Symmetry] #generators: 283, average support size: 923.074
[Symmetry] 20357 orbits with sizes: 280,144,144,144,105,105,105,105,70,70,...
[Symmetry] Num fixable by binary propagation in orbit: 41 / 280
[Symmetry] Num fixable by intersecting at_most_one with orbits: 283 largest_orbit: 280
[Symmetry] Found orbitope of size 492 x 48
[Probing] implications and bool_or (work_done=124690).
[DetectDuplicateConstraints] #duplicates=0 #without_enforcements=0 time=0.0549073s
[DetectDominatedLinearConstraints] #relevant_constraints=1000 #work_done=1674932 #num_inclusions=0 #num_redundant=0 time=0.0069748s
[ProcessSetPPC] #relevant_constraints=3000 #num_inclusions=2000 work=5049235 time=0.115019s
[FindBigHorizontalLinearOverlap] #blocks=0 #saved_nz=0 #linears=1000 #work_done=4.88218e+08/1e+09 time=1.55931s
[FindBigVerticalLinearOverlap] #blocks=0 #nz_reduction=0 #work_done=10000609 time=0.00395087s
[MergeClauses] #num_collisions=0 #num_merges=0 #num_saved_literals=0 work=0/100000000 time=0.000835822s
[Symmetry] Graph for symmetry has 490637 nodes and 1218836 arcs.
[Symmetry] GraphSymmetryFinder error: Some automorphisms were found, but probably not all.
[Symmetry] Symmetry computation done. time: 0.790599 dtime: 1
[Symmetry] #generators: 239, average support size: 913.155
[Symmetry] 19891 orbits with sizes: 350,180,140,140,105,105,84,80,72,72,...
[Symmetry] Num fixable by binary propagation in orbit: 43 / 350
[Symmetry] Num fixable by intersecting at_most_one with orbits: 239 largest_orbit: 350
[Symmetry] Found orbitope of size 504 x 35
[Probing] implications and bool_or (work_done=125990).
[DetectDuplicateConstraints] #duplicates=0 #without_enforcements=0 time=0.0553735s
[DetectDominatedLinearConstraints] #relevant_constraints=1000 #work_done=1634718 #num_inclusions=0 #num_redundant=0 time=0.007073s
[ProcessSetPPC] #relevant_constraints=3000 #num_inclusions=2000 work=5035574 time=0.117418s
[FindBigHorizontalLinearOverlap] #blocks=0 #saved_nz=0 #linears=1000 #work_done=4.87028e+08/1e+09 time=1.56874s
[FindBigVerticalLinearOverlap] #blocks=0 #nz_reduction=0 #work_done=10000854 time=0.00398422s
[MergeClauses] #num_collisions=0 #num_merges=0 #num_saved_literals=0 work=0/100000000 time=0.000857392s
[Symmetry] Graph for symmetry has 490042 nodes and 1215861 arcs.
[Symmetry] GraphSymmetryFinder error: Some automorphisms were found, but probably not all.
[Symmetry] Symmetry computation done. time: 0.822907 dtime: 1.00025
[Symmetry] #generators: 213, average support size: 894.197
[Symmetry] 19924 orbits with sizes: 234,104,84,72,72,68,68,68,65,63,...
[Symmetry] Num fixable by binary propagation in orbit: 29 / 234
[Symmetry] Num fixable by intersecting at_most_one with orbits: 213 largest_orbit: 234
[Symmetry] Found orbitope of size 420 x 21
[Probing] implications and bool_or (work_done=128760).
[DetectDuplicateConstraints] #duplicates=0 #without_enforcements=0 time=0.0555432s
[DetectDominatedLinearConstraints] #relevant_constraints=1000 #work_done=1633844 #num_inclusions=0 #num_redundant=0 time=0.00690526s
[ProcessSetPPC] #relevant_constraints=3000 #num_inclusions=2000 work=5031817 time=0.11743s
[FindBigHorizontalLinearOverlap] #blocks=0 #saved_nz=0 #linears=1000 #work_done=4.86602e+08/1e+09 time=1.61023s
[FindBigVerticalLinearOverlap] #blocks=0 #nz_reduction=0 #work_done=10000408 time=0.00412453s
[MergeClauses] #num_collisions=0 #num_merges=0 #num_saved_literals=0 work=0/100000000 time=0.00100742s
[ExpandObjective] #propagations=0 #entries=0 #tight_variables=0 #tight_constraints=0 #expands=0 #issues=0 time=0.0363259s
"""


from .log_block import LogBlock
import typing


class PresolveLogBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        super().__init__(lines)

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        return lines[0].strip().startswith("Starting presolve at") if lines else False

    def get_title(self) -> str:
        return "Presolve Log"

    def get_help(self) -> typing.Optional[str]:
        return """
        This block contains the presolve log.
        It contains information about the presolve steps and the time they took.

        There are multiple rounds of domain reduction, expansion, equivalence
        checking, substitution, and probing performed during presolve.
        These steps can take some time, but they can also significantly reduce
        the model size and the search space and thus the time it takes to find
        a solution. Usually, the summary is sufficient to look at to see what happened.

        However, you may still want to scroll over the log for messages like
          `removed duplicate constraint`, indicating redundancies (and possibly bugs)
          in you model building.
        """

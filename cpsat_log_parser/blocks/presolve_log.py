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
        The next block represents the presolve phase, an essential component of CP-SAT.
        During this phase, the solver reformulates your model for greater efficiency.
        For instance, it may detect an affine relationship between variables, such as
        `x=2y-1`, and replace `x` with `2y-1` in all constraints. It can also identify
        and remove redundant constraints or unnecessary variables. For example, the log
        entry `rule 'presolve: 33 unused variables removed.' was applied 1 time` may
        indicate that some variables created by your code were unnecessary or became
        redundant due to the reformulation. Multiple rounds of applying various rules
        for domain reduction, expansion, equivalence checking, substitution, and probing
        are performed during presolve. These rules can significantly enhance the
        efficiency of your model, though they may take some time to run. However, this
        time investment usually pays off during the search phase.

        The presolve log can be challenging to read, but it provides vital information
        on the simplifications and optimizations made by CP-SAT. Reviewing this log
        can help you understand the transformations applied to your model, allowing you
        to identify and address any unnecessary variables or constraints in your code.
        """

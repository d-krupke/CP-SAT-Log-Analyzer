"""What presolve did to the model, read from the initial and presolved model lines."""

from __future__ import annotations

from cpsat_logutils.schema import ModelDescription

from ..base import Context, Insight, Trigger


def objective_terms(model: ModelDescription) -> int:
    """Objective variables the model line reports (`(#bools: 80 in objective)`)."""
    total = 0
    for field in (model.num_bools_in_objective, model.num_ints_in_objective):
        if field is not None:
            total += field.value
    return total


def both_models(ctx: Context) -> tuple[ModelDescription, ModelDescription] | None:
    a, b = ctx.log.initial_model, ctx.log.presolved_model
    return (a, b) if a and b else None


class PresolveExpanded(Trigger):
    order = 70
    level = "info"
    title = "Presolve expanded the model"
    growth_factor = 2
    min_variables = 1000

    def check(self, ctx: Context) -> Insight | None:
        models = both_models(ctx)
        if models is None:
            return None
        a, b = models
        if not (a.num_variables and b.num_variables):
            return None
        before, after = a.num_variables.value, b.num_variables.value
        if after <= self.growth_factor * before or after <= self.min_variables:
            return None
        return self.fire(
            f"""
            The presolved model has {after:,} variables versus {before:,} initially. Presolve
            expanded high-level constraints (e.g. AllDifferent, element, tables) into Booleans
            the propagators understand; this is normal but shows where the search effort goes.
            """,
            [b.span.start],
        )


class PresolveShrank(Trigger):
    order = 70
    level = "good"
    title = "Presolve shrank the model"
    shrink_factor = 0.5

    def check(self, ctx: Context) -> Insight | None:
        models = both_models(ctx)
        if models is None:
            return None
        a, b = models
        if not (a.num_variables and b.num_variables and a.num_variables.value):
            return None
        before, after = a.num_variables.value, b.num_variables.value
        if after >= self.shrink_factor * before:
            return None
        return self.fire(
            f"Presolve reduced the model from {before:,} to {after:,} variables.", [b.span.start]
        )


class ObjectiveRemovedByPresolve(Trigger):
    """Seen on six benchmark logs (bin packing, 2D bin packing, graph coloring, dominating set).

    Worth pointing out because the portfolio silently changes shape: the objective-based
    workers and every LNS neighborhood are dropped.
    """

    order = 70
    level = "info"
    title = "Presolve fixed the objective"

    def check(self, ctx: Context) -> Insight | None:
        models = both_models(ctx)
        if models is None:
            return None
        a, b = models
        terms = objective_terms(a)
        if not terms or objective_terms(b):
            return None
        return self.fire(
            f"""
            The objective had {terms:,} variables in the initial model and none in the presolved
            one, so presolve pinned its value to a constant and the search only had to find a
            matching solution. This also reshapes the portfolio: every worker that works on the
            objective is gone (`core`, `lb_tree_search`, `objective_lb_search`,
            `objective_shaving*`, `pseudo_costs`) and so is every LNS neighborhood (`*_lns`),
            because a neighborhood needs an objective to improve. What runs instead are the
            plain exact workers plus `ls`, `feasibility_pump` and `rins/rens`, and a strategy may
            be repeated (`default_lp(2)`) to fill the worker budget. If such a run ends UNKNOWN,
            the difficulty is pure feasibility, not optimization.
            """,
            [b.span.start],
        )

"""Insights: the colored boxes in the Overview card.

Public API of the package. The triggers themselves live one module deeper, in
``triggers/`` - one file per topic, one class per box - and are loaded by import;
``base.py`` documents how to write one.
"""

from .base import LEVELS, Context, Insight, Trigger, all_triggers, build_insights

__all__ = ["LEVELS", "Context", "Insight", "Trigger", "all_triggers", "build_insights"]

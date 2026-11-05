"""Weighted operator-template selection — package layout.

Each template declares which operators it uses. The generator picks templates
weighted by 1 / (1 + min_usage_among_template_ops) — less-used operators get
more chances. State (operator usage cache, expression-to-template-name map)
is encapsulated in `UsageState`, exposed as a module singleton.

Public API:
  UsageState, get_state, set_state           — singleton state.
  load_usage(conn)                           — refresh usage cache from DB.
  record_expr_template, lookup_expr_template — expr -> template-name bookkeeping
                                               (lookup consumes; peek does not).
  get_weight(operators)                      — inverse-min-usage weight.
  weighted_choice(templates_with_ops, ...)   — biased template picker.
"""

from generator.weighted_selection.choice import (
    EPS_FRACTION,
    _feedback_loop_enabled,
    weighted_choice,
)
from generator.weighted_selection.state import (
    UsageState,
    get_state,
    get_weight,
    load_usage,
    lookup_expr_template,
    peek_expr_template,
    record_expr_template,
    set_state,
)

__all__ = [
    "EPS_FRACTION",
    "UsageState",
    "_feedback_loop_enabled",
    "get_state",
    "get_weight",
    "load_usage",
    "lookup_expr_template",
    "peek_expr_template",
    "record_expr_template",
    "set_state",
    "weighted_choice",
]

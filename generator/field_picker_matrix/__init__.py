"""Pick MATRIX fields — package layout.

Public API:
  pick_matrix              — pick `count` MATRIX field IDs.
  set_target_category      — steer subsequent picks to a target pyramid category.
  get_target_category      — read the current target.

When a target_category is set, pick_matrix guarantees at least one field
comes from that category — so the resulting alpha will be attributed to the
target pyramid (region, delay, category). The remaining fields keep the
historical 90% same-dataset bias for unit safety.
"""

from generator.field_picker_matrix.pick import pick_matrix
from generator.field_picker_matrix.target import (
    get_target_category,
    set_target_category,
)

__all__ = ["get_target_category", "pick_matrix", "set_target_category"]

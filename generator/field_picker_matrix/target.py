"""Module-level singleton for the current target pyramid category.

Set by the explorer before calling generate_expressions; cleared after.
Avoids threading the param through every call site in random_generator_build.
"""

from __future__ import annotations

_current_target_category: str | None = None


def set_target_category(category: str | None) -> None:
    """Set/clear the target pyramid category for subsequent pick_matrix calls."""
    global _current_target_category
    _current_target_category = category


def get_target_category() -> str | None:
    return _current_target_category

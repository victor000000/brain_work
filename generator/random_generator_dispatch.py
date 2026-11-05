"""Field-pool memo and template dispatch for the built-in builders.

Split out of `generator/random_generator_build.py`, which re-exports these
names (tests reach for `_field_pool` through it).
"""

import random

import generator.weighted_selection as ws
from generator.field_picker import get_cache
from generator.registry import template_uses_pool
from generator.templates_brain_website_pick import _maybe_backfill

# Redraws allowed when the two halves of a 4/5-field combo come out identical.
# `rank(X - X)` is identically zero, so such a draw is pure waste.
HALF_REDRAWS = 4

_pool_source = None
_pool: list[str] = []


def _field_pool() -> list[str]:
    """Flat MATRIX-field pool for pool-based templates, rebuilt per field load.

    Keyed on the identity of `matrix_by_dataset` itself: `load_all_fields`
    rebinds that dict on the module-singleton cache when the region changes, so
    keying on the *cache* (which never changes identity) would keep the first
    region's fields for the whole run and hand later regions fields that do not
    exist there.
    """
    global _pool, _pool_source
    matrix = get_cache().matrix_by_dataset
    if matrix is not _pool_source:
        _pool = [f for fields in matrix.values() for f in fields]
        _pool_source = matrix
    return _pool


def _call_template(fn, fields):
    """Call a registry template under its own convention.

    Pool-based templates receive the region's field pool and the `random`
    module (see `registry.template_uses_pool`); two-field templates receive the
    picked fields. Returns None when the template cannot fill.
    """
    if template_uses_pool(fn):
        return fn(_field_pool(), random)
    # The HKG interval wrap applies here too: `quantile_ts_rank(pv37_high_12,
    # 250)` is one of the measured CONCENTRATED_WEIGHT failures, and its
    # field arrives through this call, not through a picker.
    return fn(_maybe_backfill(fields[0]), _maybe_backfill(fields[1]))


def _release(*expressions):
    """Consume template-tracking entries for halves that will not be used.

    Intermediates are recorded when built; every path that discards one must
    release it, or the map grows for the process's lifetime.
    """
    for expr in expressions:
        ws.lookup_expr_template(expr)

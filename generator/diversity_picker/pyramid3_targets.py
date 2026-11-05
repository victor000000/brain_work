"""Satisfiable pyramid-target rows, and the posterior that weights them.

A target row is only eligible when the chosen cell's field pool can satisfy
it. Split out of `generator/diversity_picker/pyramid3.py`, which re-exports
these names so existing imports keep resolving.
"""

from core.db import DBError
from core.scope import in_scope, scope_sql
from generator.diversity_picker._log import dlog
from generator.field_queries import COVERAGE_OK, identifier_filter, not_label_filter
from tools.refresh_pyramid_targets.quarter import quarter_bounds

# Category used when no pyramid_targets row can be satisfied. Price data is
# always in scope, so a pv target is always meaningful; the picker degrades to
# untargeted picking only if even that has no fields.
FALLBACK_CATEGORY = "pv"

# One DISTINCT scan answers "which categories have a MATRIX field" for every
# config at once — cheaper than loading each candidate's full pool. The
# predicate mirrors field_queries_matrix.query_matrix_fields (type, coverage
# and identifier exclusions) so target and pool agree on what "has a usable
# field" means; the shared scope helper keeps the category list in sync with
# core.scope.
_AVAILABLE_SQL = f"""
    SELECT DISTINCT region, universe, delay, category_id FROM data_fields
    WHERE type='MATRIX' AND {COVERAGE_OK} AND date_coverage >= 0.5
      AND {identifier_filter()}
      {not_label_filter()}
      AND {scope_sql("category_id")}
"""


def _available_categories(conn, configs):
    """{config -> set(category_id)} for MATRIX datasets, or None if unreadable.

    A missing/legacy schema (no `data_fields` table) returns None: the caller
    then skips the satisfiability filter instead of failing generation.
    """
    try:
        rows = conn.execute(_AVAILABLE_SQL).fetchall()
    except DBError as err:
        dlog.warning("pyramid3: field availability unavailable (%s); target filter skipped", err)
        return None
    available: dict = {(r, u, d): set() for r, u, d in configs}
    for region, universe, delay, category in rows:
        key = (region, universe, delay)
        if category and key in available:
            available[key].add(category)
    return available


def _eligible_rows(conn, configs):
    """Target rows the field pool can satisfy, each with its configs.

    Returns (pyramid_targets row, [configs that can satisfy it]) pairs: a row
    is kept only when its category is in scope and at least one config with the
    same (region, delay) has a MATRIX dataset of that category, so the returned
    target can actually be honoured by pick_matrix.

    Eligibility is satisfiability, nothing else — the `score > 0` filter that
    used to live here was a *value* test wearing a satisfiability function's
    name, and it silently removed the only cell that yields. `score` is
    `gap_to_3 * multiplier`, so it is exactly 0 for a pyramid we have filled;
    measured 2026-10-10, HKG's pv row went 4.5 -> 0.0 when its 16th alpha landed
    against a target of 3, and HKG — 328 alphas above the floor in four days
    against 31 for every other region combined — stopped being generated for
    15 hours. Value belongs in the weight; see `_weighted_choice`.
    """
    try:
        rows = conn.execute(
            "SELECT region, delay, category, score FROM pyramid_targets WHERE period_start=? AND period_end=?",
            quarter_bounds(),
        ).fetchall()
    except DBError as err:
        dlog.warning("pyramid3: dated targets unavailable (%s); use untargeted fallback", err)
        return []
    if not rows:
        return []
    config_by_rd: dict = {}
    for r, u, d in configs:
        config_by_rd.setdefault((r, d), []).append((r, u, d))
    rows = [row for row in rows if in_scope(row[2]) and (row[0], row[1]) in config_by_rd]
    if not rows:
        return []

    available = _available_categories(conn, configs)
    eligible = []
    for row in rows:
        candidates = config_by_rd[(row[0], row[1])]
        if available is not None:
            candidates = [cfg for cfg in candidates if row[2] in available.get(cfg, ())]
        if candidates:
            eligible.append((row, candidates))
    return eligible


def _max_posterior_per_rd():
    """Marginalize cell_yield_posterior over universe to get max per (region, delay)."""
    from generator.diversity_picker import yield_cache

    out: dict[tuple[str, int], float] = {}
    for (region, _universe, delay), post in yield_cache._yield_posterior.items():
        key = (region, delay)
        if post > out.get(key, 0.0):
            out[key] = post
    return out

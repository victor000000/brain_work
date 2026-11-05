"""The scope predicates and category-keyed tables cleanup_db prunes.

Split out of `tools/cleanup_db.py`, which re-exports both lists — the tests
read `cleanup_db.RULES` directly.

The scope predicates come from `core.scope` — the exact-`IN ('pv','option')`
predicate restated here drifted from `in_scope()`, which also accepts the
`pv-*` children.
"""

from core.scope import scope_sql

# (table, column, predicate) — predicate keeps rows that must survive
RULES = [
    ("data_fields", "category_id", scope_sql("category_id")),
    ("datasets", "category_id", scope_sql("category_id")),
    ("dataset_categories", "id", scope_sql("id")),
    ("download_log", "subcategory_id", scope_sql("subcategory_id")),
]

# Category-keyed tables. Rows for categories we can no longer generate land in
# dead pyramids; --prune-targets removes them.
TARGET_RULES = [
    ("pyramid_targets", "category"),
    ("pyramid_alpha_counts", "category"),
    ("pyramid_multipliers", "category"),
]

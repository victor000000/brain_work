"""The data scope this project operates in: price and options only.

The restriction was applied once as a cleanup (`tools/cleanup_db.py`), and it
did not hold: the pv/option field refresh calls `store_categories`, which
re-inserted all 62 categories, 55 of them out of scope. `data_fields` and
`datasets` stayed clean only because the refresh happens to fetch pv/option
subcategories — nothing forbade the rest.

So the scope is enforced here, at the *write* paths, rather than by remembering
to filter at every read. A one-shot cleanup is a state; a guard is an
invariant.

Import `ALLOWED_CATEGORIES` rather than restating `('pv', 'option')` —
`generator/field_queries.py` and `diversity_picker/pyramid3.py` already share
one copy, and this is the same list.
"""

from __future__ import annotations

ALLOWED_CATEGORIES = ("pv", "option")

_ALLOWED = frozenset(ALLOWED_CATEGORIES)


def in_scope(category) -> bool:
    """True when a category id is inside the scope.

    A category is in scope if it is one of the allowed top-level ids, or a
    child of one — the platform names children `<parent>-<child>`, e.g.
    `pv-price-volume`, `option-option-analytics`.
    """
    if not category:
        return False
    cat = str(category)
    if cat in _ALLOWED:
        return True
    return cat.split("-", 1)[0] in _ALLOWED


def out_of_scope(category) -> bool:
    """Inverse of `in_scope`, for readability at call sites."""
    return not in_scope(category)


def keep_category(row: dict, key: str = "id") -> bool:
    """Predicate for a single category/dataset row from the BRAIN API."""
    return in_scope(row.get(key))


def scope_sql(column: str) -> str:
    """SQL fragment matching in-scope rows, for the category column given.

    Built from ALLOWED_CATEGORIES so the SQL and the Python predicate cannot
    drift apart.
    """
    allowed = ", ".join(f"'{c}'" for c in ALLOWED_CATEGORIES)
    prefixes = " OR ".join(f"{column} LIKE '{c}-%'" for c in ALLOWED_CATEGORIES)
    return f"({column} IN ({allowed}) OR {prefixes})"

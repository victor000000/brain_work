"""P3 alpha-pyramid attribution.

Derives the pyramid category set for an alpha from the field IDs in its
expression. Categories are looked up in `data_fields.category_id`, which
already populates for every field. The derived set is stored as a sorted
JSON array on `alpha_results.pyramid_categories`.

The two functions are split so tests can exercise the pure derivation
without a DB:
  - `derive_pyramid_categories(expression, field_to_category)` — pure
  - `load_field_to_category(conn)` — single-shot DB read for the dict
"""

import json
import re

from core.db import OperationalError

_FIELD_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_]+\b")


def derive_pyramid_categories(expression, field_to_category):
    """Return a canonical JSON array of distinct category IDs, or None.

    `field_to_category` is a dict mapping field_id -> category_id (load via
    `load_field_to_category(conn)`).

    Returns None when the expression is empty or has no recognizable field
    tokens — preserves the difference between "tried and matched nothing"
    (None) and "parsed an empty list" (never returned by this function).
    """
    if not expression:
        return None
    tokens = set(_FIELD_TOKEN_RE.findall(expression))
    cats = sorted({field_to_category[t] for t in tokens if t in field_to_category})
    return json.dumps(cats, separators=(",", ":")) if cats else None


def load_field_to_category(conn):
    """Load data_fields.id -> category_id once. Rows with NULL category skipped.

    Same field id may appear in multiple regions; if categories collide
    (rare — datasets are typically named per category), first wins.

    Returns an empty dict when data_fields does not yet exist (e.g. a fresh
    test database that has not downloaded field metadata).
    """
    out = {}
    try:
        for fid, cat in conn.execute("SELECT id, category_id FROM data_fields WHERE category_id IS NOT NULL"):
            out.setdefault(fid, cat)
    except OperationalError:
        # Table absent in a fresh or test DB. Narrow on purpose: a bare
        # `except Exception` here also swallowed lock timeouts and schema
        # errors, turning them into a silent empty category map.
        return out
    return out

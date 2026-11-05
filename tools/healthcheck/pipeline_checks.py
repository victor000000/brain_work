"""Checks on the refresh marker, the template registry and the generator.

Split out of `tools/healthcheck/checks.py`, which re-exports these names.
"""

import time

from tools.healthcheck.check_base import _parse_utc, check
from tools.healthcheck.thresholds import FIELD_REFRESH_KEY, FIELDS_MAX_AGE_DAYS


def check_field_freshness(conn):
    """The pv/option refresh must have run recently (metadata marker)."""
    print("\n[Field Freshness]")
    row = conn.execute("SELECT value FROM metadata WHERE key=?", (FIELD_REFRESH_KEY,)).fetchone()
    if not row:
        return check("pv/option refresh recorded", False, f"metadata has no {FIELD_REFRESH_KEY}")
    ts = _parse_utc(row[0])
    if ts is None:
        return check("pv/option refresh recorded", False, f"unparseable timestamp: {row[0]!r}")
    age_days = (time.time() - ts) / 86400
    return check(
        "pv/option refresh recent",
        age_days <= FIELDS_MAX_AGE_DAYS,
        f"last refresh {row[0]} ({age_days:.1f} days ago, limit {FIELDS_MAX_AGE_DAYS})",
    )


def check_templates():
    """Check templates are loaded and cover enough operators."""
    print("\n[Templates]")
    from generator.registry import ALL_TEMPLATES

    ok = check("Templates loaded", len(ALL_TEMPLATES) >= 5, f"{len(ALL_TEMPLATES)} templates")
    ops = set()
    for _fn, op_list in ALL_TEMPLATES:
        ops.update(op_list)
    # cnhkmcp pruned set covers a small focused operator surface
    ok &= check("Operators covered", len(ops) >= 5, f"{len(ops)} operators")
    return ok


def check_generator(conn):
    """Check expression generation works."""
    print("\n[Generator]")
    from generator.random_generator import generate_expressions

    exprs = generate_expressions(conn, "USA", 1, "TOP3000", 3)
    ok = check("Generate expressions", len(exprs) == 3, f"{len(exprs)} generated")
    ok &= check("Balanced parentheses", all(e.count("(") == e.count(")") for e in exprs))
    return ok

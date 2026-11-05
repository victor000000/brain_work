"""cleanup_db's scope predicates must come from core.scope, not a private copy."""

from core.db import connect
from tools import cleanup_db


def test_scope_predicates_come_from_core_scope():
    """The RULES must accept pv-* children, like core.scope.in_scope()."""
    from core.scope import scope_sql

    conn = connect(":memory:")
    conn.execute("CREATE TABLE t (id TEXT, category_id TEXT, subcategory_id TEXT)")
    in_scope_values = ("pv", "pv-price-volume", "option-option")
    out_of_scope_values = ("model", "fundamental-footnotes")
    conn.executemany(
        "INSERT INTO t VALUES (?, ?, ?)",
        [(v, v, v) for v in in_scope_values + out_of_scope_values],
    )
    conn.commit()

    for _table, column, keep in cleanup_db.RULES:
        assert keep == scope_sql(column), f"{column} predicate drifted from core.scope"
        kept = {r[0] for r in conn.execute(f"SELECT {column} FROM t WHERE {keep}")}
        assert kept == set(in_scope_values)
    conn.close()

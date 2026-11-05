"""The scope guard must hold at write time, not just at cleanup time.

The pv/option restriction was applied once by tools/cleanup_db.py and did not
survive the next refresh: store_categories() re-inserted all 62 categories,
55 of them out of scope. These tests pin the guards that prevent it recurring.
"""

from core.scope import ALLOWED_CATEGORIES
from tests import test_scope_write_guard_helpers as helpers

# Bound here rather than imported by name: a direct import of `conn` would be
# shadowed by the test parameters of the same name (ruff F811).
conn = helpers.conn


def test_store_categories_drops_out_of_scope(conn):
    from download.storage import store_categories

    store_categories(conn, helpers.CATEGORIES)
    kept = {r[0] for r in conn.execute("SELECT id FROM dataset_categories")}
    assert kept == {"pv", "option", "pv-price-volume"}
    assert "model" not in kept and "model-technical" not in kept


def test_rerunning_store_categories_does_not_widen_the_table(conn):
    """The exact failure: a second call used to restore all 62 rows."""
    from download.storage import store_categories

    store_categories(conn, helpers.CATEGORIES)
    first = conn.execute("SELECT COUNT(*) FROM dataset_categories").fetchone()[0]
    store_categories(conn, helpers.CATEGORIES)
    assert conn.execute("SELECT COUNT(*) FROM dataset_categories").fetchone()[0] == first


def test_allowed_categories_are_a_list():
    assert len(ALLOWED_CATEGORIES) == 2

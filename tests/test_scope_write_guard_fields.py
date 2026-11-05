"""store_data_fields must drop out-of-scope fields at write time."""

from tests import test_scope_write_guard_helpers as helpers
from tests.test_scope_write_guard_helpers import field

# Bound here rather than imported by name: a direct import of `conn` would be
# shadowed by the test parameters of the same name (ruff F811).
conn = helpers.conn


def test_store_data_fields_drops_out_of_scope(conn):
    from download.storage_fields import store_data_fields

    store_data_fields(
        conn,
        [
            field("close", "pv", "pv1"),
            field("mdl_x", "model", "mdl216"),
            field("opt_iv", "option", "option8"),
        ],
    )
    kept = {r[0] for r in conn.execute("SELECT id FROM data_fields")}
    assert kept == {"close", "opt_iv"}
    assert {r[0] for r in conn.execute("SELECT id FROM datasets")} == {"pv1", "option8"}


def test_storing_out_of_scope_only_leaves_tables_empty(conn):
    from download.storage_fields import store_data_fields

    store_data_fields(conn, [field("mdl_x", "model", "mdl216")])
    assert conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0

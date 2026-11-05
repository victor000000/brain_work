"""Healthcheck checks — thresholds, scope invariants, freshness, exit status.

The old checks queried the dropped `field_blacklist` table and compared an
in-scope pv/option database against pre-cleanup thresholds, so `make health`
crashed rather than reporting. These tests run the checks against a temp DB.
"""

from datetime import timedelta

from tests import test_healthcheck_helpers as hc
from tests.test_healthcheck_helpers import _seed_healthy, _ts
from tools.healthcheck import checks

conn = hc.conn  # the shared fixture, registered here for the tests below


# ── scope invariant ───────────────────────────────────────────────


def test_scope_check_passes_on_clean_tables(conn):
    _seed_healthy(conn)
    assert checks.check_scope(conn) is True


def test_scope_check_flags_out_of_scope_dataset_category(conn):
    _seed_healthy(conn)
    conn.execute("INSERT INTO dataset_categories VALUES ('model', 'Model', NULL)")
    assert checks.check_scope(conn) is False


def test_scope_check_flags_non_pv_category_in_fields_and_datasets(conn):
    _seed_healthy(conn)
    conn.execute("INSERT INTO data_fields VALUES ('mdl_x', 'model', 'mdl1', 'USA', 1, 'TOP3000')")
    conn.execute("INSERT INTO datasets VALUES ('mdl1', 'Model', 'model', 'USA', 1, 'TOP3000')")
    assert checks.check_scope(conn) is False


def test_scope_check_accepts_pv_children(conn):
    """in_scope() accepts `pv-*` children; the SQL predicate must too."""
    _seed_healthy(conn)
    conn.execute("INSERT INTO dataset_categories VALUES ('pv-relationship', 'Relationship', 'pv')")
    conn.execute("INSERT INTO data_fields VALUES ('rel', 'pv-relationship', 'pv2', 'USA', 1, 'TOP3000')")
    conn.execute("INSERT INTO datasets VALUES ('pv2', 'Rel', 'pv-relationship', 'USA', 1, 'TOP3000')")
    assert checks.check_scope(conn) is True


def test_scope_check_flags_null_category_rows(conn):
    """A NULL category is not in scope: `in_scope(None)` is False.

    `NOT (col IN (...))` evaluates to NULL for a NULL row, so before the fix a
    category-less row was silently counted as clean.
    """
    _seed_healthy(conn)
    conn.execute("INSERT INTO data_fields VALUES ('orphan', NULL, 'pv1', 'USA', 1, 'TOP3000')")
    conn.execute("INSERT INTO datasets VALUES ('orphan_ds', 'Orphan', NULL, 'USA', 1, 'TOP3000')")
    assert checks.check_scope(conn) is False


# ── field freshness ───────────────────────────────────────────────


def test_field_freshness_recent_passes(conn):
    _seed_healthy(conn)
    assert checks.check_field_freshness(conn) is True


def test_field_freshness_stale_fails(conn):
    _seed_healthy(conn)
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES ('last_pv_option_refresh', ?)",
        (_ts(-timedelta(days=checks.FIELDS_MAX_AGE_DAYS + 1)),),
    )
    assert checks.check_field_freshness(conn) is False


def test_field_freshness_missing_marker_fails(conn):
    _seed_healthy(conn)
    conn.execute("DELETE FROM metadata WHERE key='last_pv_option_refresh'")
    assert checks.check_field_freshness(conn) is False

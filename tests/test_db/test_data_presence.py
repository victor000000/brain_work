"""Live-DB sanity: the field pool holds price/options data and nothing else.

The database was pruned on 2026-10-02 (`tools/cleanup_db.py`) to the pv/option
categories only, and `field_blacklist` was dropped — generation is
category-filtered, with no per-field blocking.

These are integration checks against the real corpus; they skip (rather than
fail) on a checkout without brain_data.duckdb.
"""

ALLOWED = {"pv", "option"}


def test_data_fields_exist(prod_conn):
    count = prod_conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0]
    assert count > 100000, f"Expected 100K+ fields, got {count}"


def test_data_fields_are_price_and_options_only(prod_conn):
    """No fundamental/analyst/news/model rows survived the prune."""
    cats = {row[0] for row in prod_conn.execute("SELECT DISTINCT category_id FROM data_fields")}
    assert cats <= ALLOWED, f"unexpected categories in data_fields: {cats - ALLOWED}"


def test_datasets_are_price_and_options_only(prod_conn):
    cats = {row[0] for row in prod_conn.execute("SELECT DISTINCT category_id FROM datasets")}
    assert cats <= ALLOWED, f"unexpected categories in datasets: {cats - ALLOWED}"


def test_field_blacklist_is_gone(prod_conn):
    """Deliberately removed — the pool is category-filtered, not field-blocked."""
    row = prod_conn.execute(
        "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='main' AND table_name='field_blacklist'"
    ).fetchone()
    assert row is None, "field_blacklist should have been dropped"

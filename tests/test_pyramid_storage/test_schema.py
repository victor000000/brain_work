"""Schema + index existence tests for pyramid_multipliers / pyramid_alpha_counts."""

from core.db import init_tables
from tests.test_pyramid_storage.conftest import mem_conn


def test_pyramid_tables_exist():
    """Both pyramid tables created by init_tables."""
    conn = mem_conn()
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE'"
        )
    }
    assert "pyramid_multipliers" in tables
    assert "pyramid_alpha_counts" in tables


def test_pyramid_multipliers_schema():
    """pyramid_multipliers has the expected columns and PK."""
    conn = mem_conn()
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(pyramid_multipliers)")}
    assert set(cols) == {"category", "region", "delay", "multiplier", "fetched_at"}
    # PK = (category, region, delay, fetched_at) — all four pk columns flagged.
    pk_cols = sorted(name for name, row in cols.items() if row[5] > 0)
    assert pk_cols == ["category", "delay", "fetched_at", "region"]


def test_pyramid_alpha_counts_schema():
    """pyramid_alpha_counts has the expected columns and PK."""
    conn = mem_conn()
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(pyramid_alpha_counts)")}
    assert set(cols) == {"category", "region", "delay", "alpha_count", "fetched_at"}
    pk_cols = sorted(name for name, row in cols.items() if row[5] > 0)
    assert pk_cols == ["category", "delay", "fetched_at", "region"]


def test_pyramid_indexes_exist():
    """Both fetched_at indexes created."""
    conn = mem_conn()
    indexes = {
        row[0] for row in conn.execute("SELECT index_name AS name FROM duckdb_indexes() WHERE schema_name='main'")
    }
    assert "idx_pmult_fetched_at" in indexes
    assert "idx_palpha_fetched_at" in indexes


def test_init_tables_idempotent():
    """Calling init_tables twice on the same conn does not raise."""
    conn = mem_conn()
    init_tables(conn)  # second call

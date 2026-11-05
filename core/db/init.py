"""init_tables — apply DDL + idempotent column-add migrations."""

from core.db.migrations import (
    ensure_expected_multiplier_column,
    ensure_polish_tried_column,
    ensure_pyramid_categories_column,
    ensure_template_column,
)
from core.db.schema_sql import SCHEMA_SQL


def init_tables(conn):
    """Create all simulation-related tables if they don't exist, then
    apply ALTER-style migrations idempotently."""
    conn.executescript(SCHEMA_SQL)
    ensure_template_column(conn)
    ensure_pyramid_categories_column(conn)
    ensure_expected_multiplier_column(conn)
    ensure_polish_tried_column(conn)
    conn.commit()

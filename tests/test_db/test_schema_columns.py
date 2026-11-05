"""Schema-column tests for cell_priors, submission_outcomes, and migrations.

Runs against a throwaway database, never the production one — these tests
execute DDL/migrations, and `get_conn()` points at the live DB.
"""

import pytest

from core.db import connect, init_tables


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "test.duckdb")
    init_tables(c)
    yield c
    c.close()


def test_cell_priors_table_exists(conn):
    """cell_priors table created by init_tables with the documented columns and PK."""
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(cell_priors)")}
    assert set(cols) == {
        "template",
        "region",
        "universe",
        "delay",
        "count",
        "hits",
        "hit_weight",
        "expected_multiplier",
        "oos_robustness",
        "quarantined",
        "quarantined_at",
        "refreshed_at",
    }
    pk_cols = sorted(name for name, row in cols.items() if row[5] > 0)
    assert pk_cols == ["delay", "region", "template", "universe"]


def test_submission_outcomes_table_exists(conn):
    """submission_outcomes table created with full-cell PK including neutralization."""
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(submission_outcomes)")}
    assert set(cols) == {
        "template",
        "region",
        "universe",
        "delay",
        "neutralization",
        "submitted",
        "rejected",
        "throttled",
    }
    pk_cols = sorted(name for name, row in cols.items() if row[5] > 0)
    assert pk_cols == ["delay", "neutralization", "region", "template", "universe"]


def test_alpha_results_has_template_column(conn):
    """init_tables adds the `template` column idempotently."""
    init_tables(conn)  # second call must not raise
    cols = {row[1] for row in conn.execute("PRAGMA table_info(alpha_results)")}
    assert "template" in cols


def test_alpha_results_has_pyramid_categories_column(conn):
    """init_tables adds the pyramid_categories column idempotently."""
    init_tables(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(alpha_results)")}
    assert "pyramid_categories" in cols


def test_cell_priors_has_expected_multiplier_column(conn):
    """init_tables adds the expected_multiplier column idempotently with default 1.0."""
    init_tables(conn)
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(cell_priors)")}
    assert "expected_multiplier" in cols
    # Column index 4 is dflt_value in PRAGMA table_info.
    default_value = cols["expected_multiplier"][4]
    assert default_value == "1.0"


def test_cell_priors_has_oos_robustness_column(conn):
    """init_tables adds the oos_robustness column idempotently with default 0.5."""
    init_tables(conn)
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(cell_priors)")}
    assert "oos_robustness" in cols
    default_value = cols["oos_robustness"][4]
    assert default_value == "0.5"

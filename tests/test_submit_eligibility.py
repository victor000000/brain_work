"""Tests for the shared submit-eligibility SQL gate."""

from core.db import connect
from runner.submit.eligibility import (
    MIN_FITNESS,
    MIN_SHARPE,
    MIN_TEST_SHARPE,
    TURNOVER_MAX,
    TURNOVER_MIN,
    eligibility_clause,
)


def test_clause_mentions_each_column_and_threshold():
    """The fragment must reference each gated column with its constant in context."""
    clause = eligibility_clause()
    expected_fragments = (
        f"is_sharpe >= {MIN_SHARPE}",
        f"is_fitness >= {MIN_FITNESS}",
        f"is_turnover BETWEEN {TURNOVER_MIN} AND {TURNOVER_MAX}",
        f"test_sharpe > {MIN_TEST_SHARPE}",
    )
    for fragment in expected_fragments:
        assert fragment in clause, f"missing fragment {fragment!r} in clause: {clause}"


def test_clause_wrapped_in_outer_parens():
    """One outer pair of parens lets callers stitch with AND safely."""
    clause = eligibility_clause().strip()
    assert clause.startswith("(") and clause.endswith(")"), clause


def _seed_alpha_results(conn):
    """Create alpha_results with one row per rejection case + one eligible row."""
    conn.execute("""
        CREATE TABLE alpha_results (
            alpha_id TEXT PRIMARY KEY,
            is_sharpe REAL, is_fitness REAL, is_turnover REAL, test_sharpe REAL
        )
    """)
    conn.executemany(
        "INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?)",
        [
            ("eligible", 2.00, 1.20, 0.30, 0.50),  # passes everything
            ("low_sharpe", 1.20, 1.20, 0.30, 0.50),  # sharpe below MIN_SHARPE
            ("low_fitness", 2.00, 0.80, 0.30, 0.50),  # fitness below MIN_FITNESS
            ("low_turnover", 2.00, 1.20, 0.005, 0.50),  # turnover below TURNOVER_MIN
            ("high_turnover", 2.00, 1.20, 0.90, 0.50),  # turnover above TURNOVER_MAX
            ("neg_test", 2.00, 1.20, 0.30, -0.10),  # test_sharpe at/below floor
        ],
    )
    conn.commit()


def test_clause_selects_only_eligible_row_end_to_end():
    """Run the clause against in-memory DuckDB and assert it gates correctly."""
    conn = connect(":memory:")
    _seed_alpha_results(conn)
    rows = conn.execute(f"SELECT alpha_id FROM alpha_results WHERE {eligibility_clause()} ORDER BY alpha_id").fetchall()
    assert [r[0] for r in rows] == ["eligible"]
    conn.close()

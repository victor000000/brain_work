"""In-memory DB factory + blacklist-table seeder for the group-unit tests."""

from core.db import connect


def make_test_conn():
    """In-memory DB seeded with minimal schema + fixture rows for offender tests."""
    conn = connect(":memory:")
    conn.executescript("""
        CREATE TABLE data_fields (
            id TEXT, type TEXT, region TEXT, description TEXT
        );
        CREATE TABLE simulations (
            sim_id TEXT PRIMARY KEY, expression TEXT, region TEXT,
            status TEXT, error_message TEXT
        );
    """)
    conn.executemany(
        "INSERT INTO data_fields VALUES (?, ?, ?, ?)",
        [
            ("price", "MATRIX", "USA", "Stock price"),
            ("group_id", "MATRIX", "USA", "Industry grouping using method 1"),
            ("group_id", "MATRIX", "CHN", "Industry grouping using method 1"),
            ("safe_field", "MATRIX", "USA", "weighted average price aggregated within GICS industry grouping"),
            ("vec_only", "VECTOR", "USA", "vector field"),
        ],
    )
    conn.executemany(
        "INSERT INTO simulations (sim_id, expression, region, status, error_message) VALUES (?, ?, ?, ?, ?)",
        [
            (
                "s1",
                "rank(group_id)",
                "USA",
                "ERROR",
                'Incompatible unit for input of "rank" at index 0, expected "Unit[]", found "Unit[Group:1]".',
            ),
            (
                "s2",
                "rank(group_id + price)",
                "CHN",
                "ERROR",
                'Incompatible unit for input of "add" at index 0, expected "Unit[]", found "Unit[Group:1]".',
            ),
            ("s3", "rank(price)", "USA", "COMPLETE", None),
        ],
    )
    conn.commit()
    return conn


def add_blacklist_table(conn):
    """Match production schema in core/db.py: PK is (field_id, region)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS field_blacklist (
            field_id TEXT, region TEXT, reason TEXT,
            PRIMARY KEY (field_id, region)
        )
    """)

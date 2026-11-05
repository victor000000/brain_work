"""DDL for the pyramid_alpha_attribution table."""


def ensure_schema(conn):
    """Idempotent CREATE for pyramid_alpha_attribution (used by this tool only)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pyramid_alpha_attribution (
            alpha_id TEXT,
            pyramid_name TEXT,
            multiplier REAL,
            status TEXT,
            stage TEXT,
            region TEXT,
            universe TEXT,
            delay INTEGER,
            sharpe REAL,
            fetched_at INTEGER,
            PRIMARY KEY (alpha_id, pyramid_name, fetched_at)
        );
        CREATE INDEX IF NOT EXISTS idx_pyramid_attr_pyramid
            ON pyramid_alpha_attribution(pyramid_name);
        CREATE INDEX IF NOT EXISTS idx_pyramid_attr_status
            ON pyramid_alpha_attribution(status);
    """)
    conn.commit()

"""DuckDB connection helper for the brain_data database."""

import os

from core.db.compat import Connection, connect
from core.log import get_file_logger

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")
dblog = get_file_logger("db")


def get_conn():
    """Open a connection to the DuckDB database.

    Writes are serialized process-wide inside the connection wrapper, so this
    is safe to call from the explorer's background threads as well. DuckDB
    allows one *process* to hold the database at a time: while the explorer
    runs, tools in other processes cannot open it.
    """
    conn = connect(DB_PATH)
    dblog.debug("Connected to %s", DB_PATH)
    return conn


__all__ = ["DB_PATH", "PROJECT_DIR", "Connection", "connect", "get_conn"]

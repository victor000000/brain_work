"""Database connection + table initialization — package layout.

Public API:
  DB_PATH, PROJECT_DIR  — file-system constants.
  connect(target)       — open a DuckDB connection.
  get_conn()            — open a connection to the production database file.
  init_tables(conn)     — create/migrate all simulation-related tables.
  OperationalError, IntegrityError — driver-neutral errors.
"""

from core.db.compat import (
    Connection,
    DBError,
    IntegrityError,
    OperationalError,
    connect,
    connect_for_reading,
)
from core.db.connection import DB_PATH, PROJECT_DIR, get_conn
from core.db.init import init_tables

__all__ = [
    "DB_PATH",
    "PROJECT_DIR",
    "Connection",
    "DBError",
    "IntegrityError",
    "OperationalError",
    "connect",
    "connect_for_reading",
    "get_conn",
    "init_tables",
]

"""DuckDB driver facade with serialized writes and stable project errors.

Connection, cursor and transaction helpers preserve the project's DB-API
surface. Parameter spelling and DOUBLE precision are normalized for DuckDB.
Only DuckDB files are supported; analytics exchange uses Parquet.
"""

from core.db.compat_conn import Connection, connect, connect_for_reading  # noqa: F401
from core.db.compat_cursor import Cursor, _NoopCursor  # noqa: F401
from core.db.compat_errors import (  # noqa: F401
    DBError,
    IntegrityError,
    OperationalError,
    _translate,
)
from core.db.compat_sql import _rewrite  # noqa: F401

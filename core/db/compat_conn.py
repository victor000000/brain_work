"""DuckDB connections and read-only snapshot access.

Split out of `core/db/compat.py`, which re-exports these names; the statement
and transaction halves of Connection live in `core.db.compat_stmt` and
`core.db.compat_txn`.
"""

from pathlib import Path

import duckdb

from core.db.compat_errors import OperationalError, _translate
from core.db.compat_stmt import StatementMixin
from core.db.compat_txn import TransactionMixin
from core.log import get_file_logger


class Connection(TransactionMixin, StatementMixin):
    """A DuckDB wrapper with serialized transactions and stable errors."""

    def __init__(self, target=":memory:", read_only=False, **kwargs):
        path = str(target)
        if path.startswith("file:") or path.endswith((".sqlite", ".sqlite3")) or Path(path).name == "brain_data.db":
            raise OperationalError("Only DuckDB files are supported; use brain_data.duckdb")
        if Path(path).is_file():
            with Path(path).open("rb") as handle:
                if handle.read(16) == b"SQLite format 3\x00":
                    raise OperationalError("SQLite databases are not supported; use a DuckDB file")
        if kwargs:
            raise TypeError(f"unsupported connect() arguments: {sorted(kwargs)}")
        try:
            self._conn = duckdb.connect(path, read_only=read_only)
        except duckdb.Error as err:
            # Translation matters most here: a busy database raises
            # IOException, and callers catch OperationalError.
            raise _translate(err) from err
        self._holds_lock = False

    def __getattr__(self, name):
        return getattr(self._conn, name)


def connect(target=":memory:", **kwargs):
    """Open a DuckDB connection."""
    return Connection(target, **kwargs)


def connect_for_reading(path, **kwargs):
    """Open `path` for reading, replaying the write-ahead log if it needs it.

    A read-only open is not usable whenever the previous process exited without
    checkpointing: DuckDB has to replay the WAL before it can answer a query,
    and replaying needs write access to the database file, so the open fails
    with `Failure while replaying WAL file ... Bad file descriptor`. That is
    exactly the state an inspection tool wants to look at, so rather than
    refuse to run, fall back to a read-write open — which performs the replay —
    and say so.

    The fallback is only taken for that error. A database held by a running
    explorer must still fail loudly: it cannot be opened either way, and the
    caller's "the explorer holds the database" message is the useful one.
    """
    try:
        return connect(path, read_only=True, **kwargs)
    except OperationalError as err:
        if "replaying WAL" not in str(err):
            raise
        conn = connect(path, **kwargs)
        flog = get_file_logger("db")
        flog.info("replayed the write-ahead log for %s (read-only open needs it)", path)
        return conn

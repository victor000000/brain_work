"""Statement execution for the Connection facade: rewrite, lock, translate.

Split out of `core/db/compat.py` as the statement-running half of Connection.
"""

import duckdb

from core.db.compat_cursor import Cursor, _NoopCursor
from core.db.compat_errors import OperationalError, _translate
from core.db.compat_lock import _BEGIN_STMT, _END_STMT, _LOCK_TIMEOUT, _WRITE_LOCK
from core.db.compat_sql import _rewrite, _rewrite_params, _rewrite_real


class StatementMixin:
    """execute()/executemany()/executescript() over a duckdb connection."""

    # -- execution -----------------------------------------------------
    def execute(self, sql, params=None):
        sql = _rewrite(sql)
        if sql is None:
            return _NoopCursor()
        if params is not None and len(params) == 0:
            params = None  # DuckDB rejects an empty parameter set
        is_begin = bool(_BEGIN_STMT.match(sql))
        is_end = bool(_END_STMT.match(sql))
        acquired = False
        if is_begin and not self._holds_lock:
            if not _WRITE_LOCK.acquire(timeout=_LOCK_TIMEOUT):
                raise OperationalError("database is locked (write lock timed out)")
            self._holds_lock = acquired = True
        try:
            # Reentrant: a statement inside an owned transaction is a no-op
            # acquire, and a plain statement holds the lock just for itself.
            with _WRITE_LOCK:
                if params is None:
                    return Cursor(self, self._conn.execute(sql))
                return Cursor(self, self._conn.execute(sql, params))
        except duckdb.Error as err:
            if acquired:
                self._holds_lock = False
                _WRITE_LOCK.release()
            raise _translate(err) from err
        finally:
            if is_end and self._holds_lock:
                self._holds_lock = False
                _WRITE_LOCK.release()

    def executemany(self, sql, seq_of_params):
        sql = _rewrite(sql) or sql
        if not seq_of_params:
            # DuckDB rejects an empty parameter list; The project treats it as a
            # no-op, and callers rely on that for "nothing to write" batches.
            return _NoopCursor()
        try:
            with _WRITE_LOCK:
                return Cursor(self, self._conn.executemany(sql, seq_of_params))
        except duckdb.Error as err:
            raise _translate(err) from err

    def executescript(self, sql):
        # Scripts here are DDL, so the type and parameter rewrites apply to
        # the whole text; both are string-literal aware, so a multi-statement
        # script needs no splitting.
        sql = _rewrite_real(_rewrite_params(sql))
        try:
            with _WRITE_LOCK:
                return Cursor(self, self._conn.execute(sql))
        except duckdb.Error as err:
            raise _translate(err) from err

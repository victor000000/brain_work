"""Transactions and close for the Connection facade.

Split out of `core/db/compat.py` as the transaction half of Connection; the
lock it releases is the process-wide one in `core.db.compat_lock`.
"""

import duckdb

from core.db.compat_errors import _translate
from core.db.compat_lock import _WRITE_LOCK


class TransactionMixin:
    """commit/rollback/close and the `with conn:` protocol."""

    # -- transactions --------------------------------------------------
    def _release_owned_lock(self):
        if self._holds_lock:
            self._holds_lock = False
            _WRITE_LOCK.release()

    def commit(self):
        try:
            self._conn.commit()
        except duckdb.Error as err:
            raise _translate(err) from err
        finally:
            # A transaction we opened with BEGIN is over either way; leaving
            # the lock held would stall every other thread until timeout.
            self._release_owned_lock()

    def rollback(self):
        try:
            self._conn.rollback()
        except duckdb.TransactionException as err:
            # The project treats "rollback with nothing open" as a no-op, and
            # `with conn:` blocks roll back on every exception path.
            if "no transaction is active" not in str(err):
                raise _translate(err) from err
        except duckdb.Error as err:
            raise _translate(err) from err
        finally:
            self._release_owned_lock()

    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self._release_owned_lock()
        self._conn.close()

    def __enter__(self):
        # The prior driver deferred the BEGIN to the first statement; DuckDB autocommits
        # every statement, so `with conn:` would otherwise lose its atomicity
        # (the both-or-neither snapshot writes depend on it). Nested blocks
        # share the transaction already open.
        if not self._holds_lock:
            self.execute("BEGIN TRANSACTION")
        return self

    def __exit__(self, exc_type, exc, _tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

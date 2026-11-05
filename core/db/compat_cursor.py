"""The DB-API cursor surface over DuckDB results.

Split out of `core/db/compat.py`, which re-exports `Cursor`.
"""


class _NoopCursor:
    """Stands in for the cursor of an empty batch."""

    rowcount = 0

    def fetchone(self):
        return (None,)

    def fetchall(self):
        return []

    def fetchmany(self, *args):
        return []

    def __iter__(self):
        return iter(())


class Cursor:
    """The DB-API cursor surface: iteration, fetch*, description, rowcount.

    DuckDB's `execute()` hands back the connection itself, which cannot be
    iterated (`for row in conn.execute(...)` is everywhere in this codebase).
    """

    def __init__(self, connection, source):
        self._connection = connection
        self._source = source

    def fetchone(self):
        return self._source.fetchone()

    def fetchall(self):
        return self._source.fetchall()

    def fetchmany(self, size=None):
        return self._source.fetchmany() if size is None else self._source.fetchmany(size)

    def __iter__(self):
        while True:
            row = self._source.fetchone()
            if row is None:
                return
            yield row

    @property
    def description(self):
        return self._source.description

    @property
    def rowcount(self):
        return self._source.rowcount

    def execute(self, sql, params=None):
        """Project cursors can run further statements; keep that working."""
        return self._connection.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._source, name)

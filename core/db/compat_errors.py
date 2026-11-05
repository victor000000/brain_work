"""Driver-neutral error hierarchy for the DuckDB driver.

Split out of `core/db/compat.py`, which re-exports these names, so callers
never depend on duckdb's own exception hierarchy.
"""

import duckdb


class DBError(Exception):
    """Base class for every error raised by the database layer."""


class OperationalError(DBError):
    """The statement could not run — parse, catalog, I/O or lock failure."""


class IntegrityError(DBError):
    """A constraint was violated (unique, not-null, foreign key)."""


# Ordered most specific first; the first matching duckdb exception wins.
# Everything but a constraint violation maps to OperationalError because that
# matches the project error contract for the same situations (missing table or column,
# syntax error, lock contention) and what the existing handlers catch.
_ERROR_MAP = (
    (duckdb.ConstraintException, IntegrityError),
    (duckdb.ParserException, OperationalError),
    (duckdb.BinderException, OperationalError),
    (duckdb.CatalogException, OperationalError),
    (duckdb.TransactionException, OperationalError),
    (duckdb.IOException, OperationalError),
    (duckdb.InvalidInputException, OperationalError),
)


def _translate(err):
    """Map a duckdb exception onto this module's hierarchy."""
    for exc_type, mapped in _ERROR_MAP:
        if isinstance(err, exc_type):
            return mapped(str(err))
    return OperationalError(str(err))

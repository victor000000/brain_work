"""Parameter and DDL normalization for DuckDB."""

import re

_DDL = re.compile(r"^\s*(CREATE|ALTER)\b", re.IGNORECASE)
_REAL_TYPE = re.compile(r"\bREAL\b")
_NAMED_PARAM = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)\b")


_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")


def _outside_strings(sql, transform):
    """Apply `transform` to the parts of `sql` that sit outside '...' literals.

    Both rewrites below would otherwise corrupt ordinary SQL: a colon in
    `'%H:%M:%S'` is not a parameter, and the word REAL inside a literal is
    not a column type.
    """
    out = []
    last = 0
    for match in _STRING_LITERAL.finditer(sql):
        out.append(transform(sql[last : match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(transform(sql[last:]))
    return "".join(out)


def _rewrite_params(sql):
    """`:name` → `$name` (DuckDB's spelling), skipping `::` casts."""

    def transform(part):
        return re.sub(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)\b", r"$\1", part)

    return _outside_strings(sql, transform)


def _rewrite_real(sql):
    """`REAL` → `DOUBLE` in DDL: preserve the project's 8-byte measurement precision."""
    return _outside_strings(sql, lambda part: _REAL_TYPE.sub("DOUBLE", part))


_ADD_COLUMN_NOT_NULL = re.compile(
    r"(\bADD\s+(?:COLUMN\s+)?[\"'a-zA-Z0-9_]+\s+[a-zA-Z0-9_]+(?:\s*\([^)]*\))?)"
    r"\s+NOT\s+NULL\s+(DEFAULT\b)",
    re.IGNORECASE,
)


def _rewrite(sql):
    """Normalize supported SQL for DuckDB; unsupported statements raise."""
    sql = _ADD_COLUMN_NOT_NULL.sub(r"\1 \2", sql)
    sql = _rewrite_params(sql)
    if _DDL.match(sql):
        sql = _rewrite_real(sql)
    return sql

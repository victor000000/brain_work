"""Scan `simulations` for MATRIX fields implicated in Unit[Group:1] errors.

Split out of `download/blacklist_group_unit.py`, which re-exports these names.

Read-only: nothing here writes.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_]+\b")


def extract_field_tokens(expression: str | None, known_field_ids: set[str]) -> set[str]:
    """Return the subset of `known_field_ids` appearing as tokens in `expression`."""
    if not expression:
        return set()
    tokens = set(_TOKEN_RE.findall(expression))
    return tokens & known_field_ids


def find_group_unit_offenders(conn) -> list[tuple[str, str]]:
    """Scan `simulations` for Unit[Group:1] errors, return (field_id, region) pairs.

    Conservatively includes every MATRIX field referenced in a failing expression,
    even if it isn't strictly the cause. Returns a sorted list for deterministic
    output ordering (helps when comparing successive runs).
    """
    matrix_ids = {row[0] for row in conn.execute("SELECT id FROM data_fields WHERE type = 'MATRIX'")}
    rows = conn.execute(
        """
        SELECT expression, region FROM simulations
        WHERE error_message LIKE '%Unit[Group:1]%'
          AND expression IS NOT NULL
        """
    ).fetchall()
    offenders: set[tuple[str, str]] = set()
    for expression, region in rows:
        for field_id in extract_field_tokens(expression, matrix_ids):
            offenders.add((field_id, region))
    return sorted(offenders)

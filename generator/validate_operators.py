"""The operator allowlist — the layer `py-fastplus` intentionally does not give.

Split out of `generator/validate.py` (whose docstring covers both layers),
which re-exports these names so `from generator.validate import ...` keeps
resolving.
"""

import re

# Identifiers that are called as functions in an expression. Case-insensitive:
# BRAIN operator names are lowercase, so an upper-case call (`Max(`, `STR(`) is
# either an invented operator or a mis-cased field used as one. Both must be
# seen and rejected by the allowlist — a lowercase-only regex skips them and
# fastplus, which is case-insensitive, waves them through.
_CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.IGNORECASE)

# Words that look like calls but are not operators: the literals, and the
# keywords that only appear inside a call's syntax.
#
# `and`, `or` and `not` were in this set as "syntax" and are not: the platform's
# own `operators` table defines them, category Logical, as `and(input1, input2)`
# — functions like any other, with no infix form in Fast Expression. Being
# listed here made a logical call invisible to the allowlist, so `and(...)`
# could call anything without `and` being a known operator, and invisible to
# `tests/test_templates_operators.py`'s tag check, which reported `and` as
# "never emitted" for a template that emits it (found 2026-10-12, adding
# `double_gated_momentum`).
_NOT_OPERATORS = {
    "nan",
    "inf",
    "true",
    "false",
    "if",
    "else",
}


def load_operator_names(conn) -> set[str]:
    """Operator names from the `operators` table (platform's own list)."""
    return {row[0] for row in conn.execute("SELECT name FROM operators") if row[0]}


def called_identifiers(expression: str) -> set[str]:
    """Identifiers used as function calls in `expression` (case preserved).

    The returned names keep their original spelling, so the allowlist check
    reports `Max` rather than silently lower-casing it to the real `max`.
    """
    return {m for m in _CALL_RE.findall(expression) if m.lower() not in _NOT_OPERATORS}

"""Slot and value-token checks for mined template skeletons.

Split out of `generator/template_fill.py`, which re-exports every name here so
`from generator.template_fill import ...` keeps resolving.
"""

from __future__ import annotations

import re

SLOT = "{f}"

# An identifier not immediately followed by `(` is a value, not an operator
# call. Case-insensitive for the same reason as validate._CALL_RE: `Vvolume`
# is a mis-cased field and must be seen (and then rejected by the field check)
# rather than skipped as if it were syntax.
_VALUE_TOKEN_RE = re.compile(r"\b([a-z][a-z0-9_]*)\b(?!\s*\()", re.IGNORECASE)

# Operator argument keywords and literals — real syntax that appears where a
# field otherwise would. Deliberately *not* the single-letter placeholders
# (`x`, `y`, `d`, `n`, ...) that mined skeletons use for variables: those must
# fail the field check, or filling emits `ts_delta(x, d)` — an expression over
# undefined names that fastplus happily parses.
#
# The parameter names are the platform's own, read off the `definition` column
# of the `operators` table (`hump(x, hump = 0.01)`, `tail(x, lower = 0,
# upper = 0, newval = 0)`, `ts_target_tvr_decay(x, ..., target_tvr=0.1)`) —
# every name the definitions spell with a `=`, plus the ones the grammar makes
# *required* keywords, which the definitions spell without one (`k` in
# `kth_element(x, d, k, ignore="NaN")`). Missing names cost a render each time:
# a named argument whose key is absent here reads as a value token, so the
# whole expression is rejected as "unknown field(s): <key>" — which is how
# `hump` (2026-10-12, `unknown field(s): hump`) and `target_tvr` (same day,
# `unknown field(s): target_tvr`) each failed every render until added.
#
# Checked against the pool before adding: none of these is the exact id of a
# field in `data_fields` (19,665 ids at 2026-10-03), so no field is hidden from
# the field check by being listed here. The comparison is whole-token, so a
# field that merely contains one (`price_limit_*) is unaffected.
KEYWORDS = {
    # Literals.
    "nan",
    "inf",
    "true",
    "false",
    # Words that appear bare inside conditions.
    "and",
    "or",
    "not",
    "if",
    "else",
    "on",
    "off",
    # Parameter names, from the platform's definitions.
    "constant",
    "dense",
    "driver",
    "filter",
    "hump",
    "ignore",
    "k",
    "lag",
    "lambda_max",
    "lambda_min",
    "limit",
    "longscale",
    "lookback",
    "lower",
    "method",
    "newval",
    "range",
    "rate",
    "rettype",
    "scale",
    "shortscale",
    "sigma",
    "std",
    "target_tvr",
    "upper",
    "useStd",
}

# Fields the platform offers that no pv/option dataset holds: the built-in
# grouping fields, valid wherever an operator wants a group.
GROUP_NAMES = {
    "sector",
    "industry",
    "subindustry",
    "market",
    "country",
    "exchange",
    "currency",
}


def slot_count(skeleton: str) -> int:
    """Number of `{f}` slots in a skeleton."""
    return skeleton.count(SLOT)


def _value_tokens(text: str) -> set[str]:
    """Identifiers `text` reads as values: calls and `{f}` slots excluded.

    KEYWORDS are dropped because they are operator arguments/literals, not
    fields; the comparison is case-sensitive so a mis-cased `Std` is still
    reported as an unknown field.
    """
    # Native bucket() accepts explicit boundaries. Exclude only the named
    # argument spelling, so a bare field named buckets still needs validation.
    text = re.sub(r"(?<=[,(])\s*buckets\s*=", "=", text)
    return {t for t in _VALUE_TOKEN_RE.findall(text.replace(SLOT, " ")) if t not in KEYWORDS}


def unknown_field_tokens(expr: str, known_fields) -> set[str]:
    """Value tokens that are neither a known field nor an allowed built-in name.

    Group names are allowed because the platform defines them (they are not in
    any dataset the pool query returns); everything else must be a field in the
    pool or the expression reads data the pv/option restriction cannot supply.
    """
    return _value_tokens(expr) - set(known_fields) - GROUP_NAMES


def field_violation(expr: str, known_fields) -> str | None:
    """Why `expr` reads an unknown field, or None. See `unknown_field_tokens`."""
    unknown = unknown_field_tokens(expr, known_fields)
    if unknown:
        return f"unknown field(s): {', '.join(sorted(unknown))}"
    return None

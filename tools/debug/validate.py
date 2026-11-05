"""Expression validation — checks operators and field names."""

import re

from tools.debug.validate_rules import SKIP_TOKENS, VALID_OPS


def check_expression(expr, valid_fields):
    """Return error string or None if OK."""
    # Check operator names
    ops = re.findall(r"([a-z_]+)\s*\(", expr)
    bad_ops = [o for o in ops if o not in VALID_OPS]
    if bad_ops:
        return f"BAD_OP: {bad_ops}"

    # Check field names exist
    tokens = re.findall(r"\b([a-z][a-z0-9_]+)\b", expr)
    fields = [t for t in tokens if t not in SKIP_TOKENS]
    bad = [f for f in fields if f not in valid_fields]
    if bad:
        return f"BAD_FIELD: {bad[:3]}"

    return None

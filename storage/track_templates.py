"""Track which template generated each alpha expression.

Uses generation-time tracking (from weighted_selection._expr_templates) when
available, falls back to regex pattern matching for historical expressions.
Recorded in template_performance table for evaluation.
"""

import re

from core.log import get_file_logger
from storage.track_signatures import TEMPLATE_SIGNATURES

alog = get_file_logger("alpha")


def identify_template(expression):
    """Identify which template generated an expression.

    First checks generation-time tracking, falls back to regex signatures.
    """
    # Try generation-time tracking (accurate for new expressions). A peek, not
    # a consuming lookup: a slotless template emits the same string every draw,
    # so consuming would attribute the first alpha of that shape and record
    # every later one as `unknown`. See `peek_expr_template`.
    from generator.weighted_selection import peek_expr_template

    tracked = peek_expr_template(expression)
    if tracked:
        return tracked

    # Fallback: regex pattern matching (for historical expressions)
    for pattern, name in TEMPLATE_SIGNATURES:
        if re.search(pattern, expression):
            return name
    return "unknown"


def record_template_performance(conn, expression, alpha_id, sharpe, test_sharpe, fitness, template_name=None):
    """Identify template (or accept a pre-resolved name) and record its performance.

    Pass `template_name` when the caller has already called `identify_template` —
    that avoids a second lookup, which used to miss the generation-time entry
    because the read consumed it. The read is a peek now, so a caller that
    passes the name is saving work rather than saving the entry.
    """
    if template_name is None:
        template_name = identify_template(expression)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS template_performance (
            alpha_id TEXT PRIMARY KEY, template_name TEXT,
            is_sharpe REAL, test_sharpe REAL, fitness REAL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO template_performance VALUES (?,?,?,?,?)",
        (alpha_id, template_name, sharpe, test_sharpe, fitness),
    )
    alog.debug("Template %s -> %s sh=%.2f", template_name, alpha_id, sharpe or 0)

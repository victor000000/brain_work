"""Resolve finite-study labels from durable simulation ownership."""

import json

from core.log import get_file_logger

alog = get_file_logger("alpha")


def probe_template(conn, sim_id, expression):
    """Return a parent-owned tag, or None for an ordinary simulation.

    Expression-only tracking cannot distinguish concurrent settings controls
    and may be overwritten before either result arrives.
    """
    row = conn.execute(
        """SELECT p.expressions, p.template_tags
             FROM simulations s JOIN probe_batches p
               ON p.parent_id = COALESCE(s.parent_id, s.sim_id)
            WHERE s.sim_id = ?""",
        (sim_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        expressions, tags = (json.loads(value) for value in row)
        if not isinstance(expressions, list) or not isinstance(tags, list) or len(expressions) != len(tags):
            raise ValueError("invalid probe label lists")
        matches = [tag for expr, tag in zip(expressions, tags, strict=True) if expr == expression]
        if len(matches) != 1 or not isinstance(matches[0], str) or not matches[0]:
            raise ValueError("missing or ambiguous probe expression label")
        return matches[0]
    except (TypeError, ValueError) as error:
        alog.warning("Probe attribution %s: %s", sim_id, error)
        return "unknown"

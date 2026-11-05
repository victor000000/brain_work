"""Complete eligible field sets for validating an already-written expression.

Generation samples a bounded number of fields per dataset. That random draw
does not decide whether a specific field exists. Reuse its scope/coverage/type
rules here without sampling, for cross-cell polish and explicit probe payloads.
"""

from generator.field_dead import cached_dead_fields
from generator.field_queries import CATEGORY_FILTER, COVERAGE_OK, identifier_filter, not_label_filter


def validation_pools(conn, region, universe, delay):
    """Return separate (matrix, vector, group) sets under the eligibility rules."""
    rows = conn.execute(
        f"""
        SELECT id, type FROM data_fields
        WHERE region=? AND universe=? AND delay=? {CATEGORY_FILTER}
          AND (
            (type='MATRIX' AND {COVERAGE_OK} AND date_coverage>=0.5
              AND {identifier_filter()} {not_label_filter()})
            OR (type='VECTOR' AND coverage>=0.3 {not_label_filter()})
            OR type='GROUP'
          )
        """,
        (region, universe, delay),
    ).fetchall()
    dead = cached_dead_fields(conn)
    matrix, vectors, groups = set(), set(), set()
    for field_id, field_type in rows:
        if field_type == "GROUP":
            groups.add(field_id)
        elif field_id not in dead:
            (vectors if field_type == "VECTOR" else matrix).add(field_id)
    return matrix, vectors, groups

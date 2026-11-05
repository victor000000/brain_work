"""Write one row per submission check, and record the durable failures.

Split out of `storage/store_checks.py`, which re-exports the name. The caller
replaces the stored check set wholesale, so it is handed back the names it saw.
"""

import json

from core.log import get_file_logger

clog = get_file_logger("check")


def _record_check_rows(conn, alpha_id, checks, now):
    """Upsert each check row and tally the outcomes.

    Returns (names_seen, pass, fail, warn, pend). `names_seen` is what lets
    `store_checks` drop the rows of a previous, larger response.
    """
    pass_count, fail_count, warn_count, pend_count = 0, 0, 0, 0
    current_names = set()
    for ch in checks:
        result = ch["result"]
        limit_v = ch.get("limit")
        actual_v = ch.get("value")
        current_names.add(ch["name"])

        # Sanitize non-scalar values
        if isinstance(limit_v, (list, dict)):
            limit_v = None
        if isinstance(actual_v, (list, dict)):
            actual_v = None

        # Scalar columns support existing reports; preserve dates, ratios and
        # structured native values in the existing JSON-capable extra column.
        conn.execute(
            "INSERT OR REPLACE INTO submission_checks VALUES (?,?,?,?,?,?)",
            (alpha_id, ch["name"], result, limit_v, actual_v, json.dumps(ch, ensure_ascii=False, sort_keys=True)),
        )

        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        elif result == "WARNING":
            warn_count += 1
        else:
            pend_count += 1

        if result == "FAIL":
            # Durable failure record (check_failures in schema_sql.py): the
            # per-alpha tables above are replaced wholesale and summarised to a
            # single row, so nothing else can answer "what keeps blocking
            # submission, and by how much, over time?". Upsert keeps first/last
            # seen and a count for repeat offenders.
            conn.execute(
                """INSERT INTO check_failures
                       (alpha_id, check_name, limit_val, actual_val,
                        first_seen, last_seen, seen_count)
                   VALUES (?,?,?,?,?,?,1)
                   ON CONFLICT (alpha_id, check_name) DO UPDATE SET
                       limit_val = EXCLUDED.limit_val,
                       actual_val = EXCLUDED.actual_val,
                       last_seen = EXCLUDED.last_seen,
                       seen_count = check_failures.seen_count + 1""",
                (alpha_id, ch["name"], limit_v, actual_v, now, now),
            )
            if limit_v is None and actual_v is None:
                clog.debug("%s FAIL %s limit=None val=None (not applicable)", alpha_id, ch["name"])
            else:
                clog.warning("%s FAIL %s limit=%s val=%s", alpha_id, ch["name"], limit_v, actual_v)

    return current_names, pass_count, fail_count, warn_count, pend_count

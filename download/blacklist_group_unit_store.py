"""Write the scan's offenders into `field_blacklist`.

Split out of `download/blacklist_group_unit.py`, which re-exports this name.
"""

from __future__ import annotations

from download.blacklist_group_unit_scan import find_group_unit_offenders


def backfill_blacklist(conn) -> int:
    """Insert offenders into field_blacklist with reason='group_unit'.

    Idempotent — INSERT OR IGNORE skips rows already present on the
    (field_id, region) PK regardless of reason. Returns the count of newly
    inserted rows.
    """
    offenders = find_group_unit_offenders(conn)
    if not offenders:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM field_blacklist").fetchone()[0]
    conn.executemany(
        "INSERT OR IGNORE INTO field_blacklist (field_id, region, reason) VALUES (?, ?, 'group_unit')",
        offenders,
    )
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM field_blacklist").fetchone()[0]
    return after - before

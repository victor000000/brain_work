"""Read the most recent consistent snapshot from the pyramid tables."""


def get_current_pyramid_state(conn):
    """Return list of dicts for the latest consistent (multipliers ⨝ counts) snapshot.

    Relies on the both-or-neither write invariant enforced by
    `store_pyramid_state`: both tables share a `fetched_at` per refresh, so
    JOIN USING the four columns naturally returns rows from the latest pair.
    If the invariant is violated by direct SQL, this helper returns 0 rows for
    the affected snapshot — fail-loud is intentional.
    """
    rows = conn.execute(
        """
        SELECT m.category, m.region, m.delay, m.multiplier, a.alpha_count, m.fetched_at
        FROM pyramid_multipliers m
        JOIN pyramid_alpha_counts a USING (category, region, delay, fetched_at)
        WHERE m.fetched_at = (SELECT MAX(fetched_at) FROM pyramid_multipliers)
        ORDER BY m.multiplier DESC, a.alpha_count ASC
        """
    ).fetchall()
    return [
        {
            "category": r[0],
            "region": r[1],
            "delay": r[2],
            "multiplier": r[3],
            "alpha_count": r[4],
            "fetched_at": r[5],
        }
        for r in rows
    ]

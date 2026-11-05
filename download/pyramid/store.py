"""Insert one consistent (multipliers + alpha_counts) snapshot per fetched_at."""


def store_pyramid_state(conn, multipliers, alpha_counts, fetched_at):
    """Insert one snapshot under `fetched_at` for both tables in a single transaction.

    Both-or-neither write invariant: either both `executemany` calls succeed
    and the transaction commits, or neither writes (the context manager rolls
    back on exception, then the exception propagates).

    Caller must supply a fresh `fetched_at`; reusing one will raise
    IntegrityError on PK collision (intentional — fail-loud, never silent
    overwrite).
    """
    with conn:
        conn.executemany(
            "INSERT INTO pyramid_multipliers (category, region, delay, multiplier, fetched_at) VALUES (?, ?, ?, ?, ?)",
            [(m["category"], m["region"], m["delay"], m["multiplier"], fetched_at) for m in multipliers],
        )
        conn.executemany(
            "INSERT INTO pyramid_alpha_counts "
            "(category, region, delay, alpha_count, fetched_at) VALUES (?, ?, ?, ?, ?)",
            [(a["category"], a["region"], a["delay"], a["alpha_count"], fetched_at) for a in alpha_counts],
        )

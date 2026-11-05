"""Per-(region, universe, delay) eligible-yield Beta-Bernoulli posterior.

Aggregated marginally over template AND neutralization, because pyramid3
selects the cell before either is chosen. The posterior is consumed by
diversity_picker.pyramid3 to scale pyramid_targets.score by empirical
hit rate.

Only reachable (pv/option) alphas count — see `aggregate.py`.
"""

import time

from core.log import get_file_logger
from generator.diversity_weights.compute_count import _REACHABLE_SQL as REACHABLE_SQL
from generator.priors_loader._constants import _YIELD_ALPHA, _YIELD_BETA

plog = get_file_logger("generator")


def fetch_yield_counts(conn):
    """Per (region, universe, delay) (count, cleared_count) tuples.

    The success term is **an alpha that cleared its checks**, not one that
    passed the local gate. The gate was the proxy here until 2026-10-12, and it
    is the quantity CHN's universe effect inflates: measured over 10-10..10-11,
    78 of 78 checked CHN/TOP2000U gate-passers failed
    `LOW_ROBUST_UNIVERSE_SHARPE`, against 0 of 32 for HKG/TOP800. Paying a cell
    for gate-passers paid it for the thing it fakes, which is why a cell with a
    0% conversion rate never lost its budget.

    Cleared-check counting separates the two cells *better* than the gate did —
    9.0x against 3.5x — so this is not a trade of signal for correctness.
    `status = 'SUBMITTED'` is the objective itself and remains too sparse to
    carry a per-cell posterior (single digits a day account-wide).

    The prior in `_constants` is calibrated to this signal's base rate, not the
    gate's: measured, a cleared check is roughly a 30th as common as a
    gate-pass, so leaving `_YIELD_ALPHA=1/_YIELD_BETA=49` would put every known
    cell far *below* `_PRIOR_MEAN` and hand the allocation to cells with no row
    at all.
    """
    return conn.execute(
        f"""
        SELECT alpha_results.region, alpha_results.universe, alpha_results.delay,
               COUNT(*) AS cnt,
               SUM(CASE WHEN s.fail_count = 0 AND s.pend_count = 0 THEN 1 ELSE 0 END) AS cleared
        FROM alpha_results
        LEFT JOIN alpha_check_summary s ON s.alpha_id = alpha_results.alpha_id
        WHERE alpha_results.template IS NOT NULL AND {REACHABLE_SQL}
        GROUP BY alpha_results.region, alpha_results.universe, alpha_results.delay
        """
    ).fetchall()


def refresh_cell_yield_posterior(conn) -> None:
    """Replace cell_yield_posterior table from current alpha_results state."""
    rows = fetch_yield_counts(conn)
    now = int(time.time())
    upserts = []
    for region, universe, delay, cnt, cleared in rows:
        # The column is still `eligible` from when the success event was the
        # local gate. What it holds is the cleared-check count; renaming it
        # needs an ALTER on a table with a documented index-desync history (see
        # the rebuild note below), which is not worth the risk for a name.
        ok = cleared or 0
        posterior = (_YIELD_ALPHA + ok) / (_YIELD_ALPHA + _YIELD_BETA + cnt)
        upserts.append((region, universe, delay, cnt, ok, posterior, now))

    with conn:
        # ── REBUILD, do not DELETE + re-INSERT ───────────────────────────────────────────
        # DuckDB 1.5.x has a recurring ART-index desync (duckdb/duckdb#23645): deleting
        # rows and inserting others with the SAME primary keys can leave the index
        # inconsistent once a checkpoint persists it — every later DELETE on the table
        # then raises a FATAL ("Failed to delete all rows from index. Only deleted 0 out
        # of 41 rows") that invalidates the whole connection, and every restart becomes a
        # crash loop. This refresh replaces every row key-for-key by design, so it is a
        # standing trigger: it took the table down twice on 2026-10-03, the second time
        # re-poisoning it immediately after a manual table rebuild.
        # DROP + CREATE rebuilds the index outright (the remedy the issue recommends), the
        # table is a derived ~41-row cache so a rebuild is free, and the DDL is read from
        # the catalog rather than restated here so it cannot drift from schema_sql.py.
        ddl = conn.execute("SELECT sql FROM duckdb_tables() WHERE table_name = 'cell_yield_posterior'").fetchone()
        if ddl is None:
            conn.execute("DELETE FROM cell_yield_posterior")  # schema not applied yet
        else:
            indexes = conn.execute(
                "SELECT sql FROM duckdb_indexes() WHERE table_name = 'cell_yield_posterior'"
            ).fetchall()
            conn.execute("DROP TABLE IF EXISTS cell_yield_posterior")
            conn.execute(ddl[0])
            for (isql,) in indexes:
                if isql:
                    conn.execute(isql)
        conn.executemany(
            """
            INSERT INTO cell_yield_posterior
              (region, universe, delay, count, eligible, posterior, refreshed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            upserts,
        )
    plog.debug("refresh_cell_yield_posterior: %d rows at t=%d", len(upserts), now)

"""DDL for the pyramid, cell-prior and submission bookkeeping tables.

Split out of `core/db/schema_sql.py`, which concatenates this after the core
tables into the single executescript-able string callers import. Idempotent —
every statement is `CREATE TABLE/INDEX IF NOT EXISTS`.
"""

PRIORS_SCHEMA_SQL = """    CREATE TABLE IF NOT EXISTS pyramid_multipliers (
        category   TEXT    NOT NULL,
        region     TEXT    NOT NULL,
        delay      INTEGER NOT NULL,
        multiplier REAL    NOT NULL,
        fetched_at INTEGER NOT NULL,
        PRIMARY KEY (category, region, delay, fetched_at)
    );
    CREATE INDEX IF NOT EXISTS idx_pmult_fetched_at
        ON pyramid_multipliers (fetched_at);
    CREATE TABLE IF NOT EXISTS pyramid_alpha_counts (
        category    TEXT    NOT NULL,
        region      TEXT    NOT NULL,
        delay       INTEGER NOT NULL,
        alpha_count INTEGER NOT NULL,
        fetched_at  INTEGER NOT NULL,
        PRIMARY KEY (category, region, delay, fetched_at)
    );
    CREATE INDEX IF NOT EXISTS idx_palpha_fetched_at
        ON pyramid_alpha_counts (fetched_at);
    CREATE TABLE IF NOT EXISTS cell_priors (
        template       TEXT    NOT NULL,
        region         TEXT    NOT NULL,
        universe       TEXT    NOT NULL,
        delay          INTEGER NOT NULL,
        count          INTEGER NOT NULL,
        hits           INTEGER NOT NULL,
        hit_weight     REAL    NOT NULL,
        expected_multiplier REAL NOT NULL DEFAULT 1.0,
        oos_robustness REAL    NOT NULL DEFAULT 0.5,
        quarantined    INTEGER NOT NULL DEFAULT 0,
        quarantined_at INTEGER,
        refreshed_at   INTEGER NOT NULL,
        PRIMARY KEY (template, region, universe, delay)
    );
    CREATE TABLE IF NOT EXISTS submission_outcomes (
        template       TEXT NOT NULL,
        region         TEXT NOT NULL,
        universe       TEXT NOT NULL,
        delay          INTEGER NOT NULL,
        neutralization TEXT NOT NULL,
        submitted INTEGER NOT NULL DEFAULT 0,
        rejected  INTEGER NOT NULL DEFAULT 0,
        throttled INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (template, region, universe, delay, neutralization)
    );
    CREATE TABLE IF NOT EXISTS pyramid_targets (
        region       TEXT    NOT NULL,
        delay        INTEGER NOT NULL,
        category     TEXT    NOT NULL,
        alpha_count  INTEGER NOT NULL DEFAULT 0,
        multiplier   REAL    NOT NULL DEFAULT 1.0,
        gap_to_3     INTEGER NOT NULL DEFAULT 3,
        score        REAL    NOT NULL DEFAULT 0,
        period_start TEXT,
        period_end   TEXT,
        refreshed_at INTEGER NOT NULL,
        PRIMARY KEY (region, delay, category)
    );
    CREATE INDEX IF NOT EXISTS idx_pyramid_targets_score
        ON pyramid_targets (score DESC);
    CREATE TABLE IF NOT EXISTS cell_yield_posterior (
        region       TEXT    NOT NULL,
        universe     TEXT    NOT NULL,
        delay        INTEGER NOT NULL,
        count        INTEGER NOT NULL,
        eligible     INTEGER NOT NULL,
        posterior    REAL    NOT NULL,
        refreshed_at INTEGER NOT NULL,
        PRIMARY KEY (region, universe, delay)
    );
    CREATE INDEX IF NOT EXISTS idx_cell_yield_posterior_post
        ON cell_yield_posterior (posterior DESC);
    -- An alpha whose check could not be decided — the correlation endpoints
    -- answering "still computing" for the whole deadline, say. It keeps no
    -- summary (it was never decided) so it stays eligible, and the checker
    -- picks by sharpe descending, so without this it would head the queue
    -- every run and, once a run is bounded by wall clock, starve everything
    -- below it. `last_at` lets the selector send it to the back.
    CREATE TABLE IF NOT EXISTS check_deferrals (
        alpha_id   TEXT PRIMARY KEY,
        attempts   INTEGER NOT NULL DEFAULT 0,
        last_at    TEXT    NOT NULL
    );
"""

"""DDL for the simulation records, results and platform checks.

Split out of `core/db/schema_sql.py`, which concatenates this with the priors
tables into the single executescript-able string callers import. Idempotent —
every statement is `CREATE TABLE/INDEX IF NOT EXISTS`.
"""

CORE_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS simulations (
        sim_id TEXT PRIMARY KEY, parent_id TEXT, batch_idx INTEGER,
        expression TEXT, region TEXT, universe TEXT, delay INTEGER,
        status TEXT, alpha_id TEXT, error_message TEXT,
        submitted_at TEXT, completed_at TEXT, raw_settings TEXT
    );
    CREATE TABLE IF NOT EXISTS alpha_results (
        alpha_id TEXT PRIMARY KEY, sim_id TEXT, expression TEXT,
        region TEXT, universe TEXT, delay INTEGER,
        neutralization TEXT, decay INTEGER, truncation REAL,
        is_sharpe REAL, is_fitness REAL, is_turnover REAL,
        is_returns REAL, is_drawdown REAL, is_margin REAL,
        is_pnl REAL, is_long_count INTEGER, is_short_count INTEGER,
        train_sharpe REAL, train_fitness REAL,
        test_sharpe REAL, test_fitness REAL,
        is_rn_sharpe REAL, is_rn_fitness REAL,
        grade TEXT, status TEXT, operator_count INTEGER,
        raw_json TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS submission_checks (
        -- limit_val/actual_val are TEXT: categorical checks report labels
        -- ('RAM', 'Industry') where numeric checks report numbers.
        alpha_id TEXT, check_name TEXT, result TEXT,
        limit_val TEXT, actual_val TEXT, extra TEXT,
        PRIMARY KEY (alpha_id, check_name)
    );
    CREATE TABLE IF NOT EXISTS alpha_check_summary (
        alpha_id TEXT PRIMARY KEY, pass_count INT, fail_count INT,
        warn_count INT, pend_count INT, checked_at TEXT
    );
    -- Durable record of every platform check FAIL, with the limit and the
    -- observed value. submission_checks is replaced wholesale per alpha and
    -- alpha_check_summary is one row per alpha, so neither can answer "what
    -- keeps blocking submission, and by how much, over time?" — this can.
    -- Upserted per (alpha, check): first/last seen + count, latest values.
    CREATE TABLE IF NOT EXISTS check_failures (
        alpha_id TEXT NOT NULL, check_name TEXT NOT NULL,
        limit_val TEXT, actual_val TEXT,
        first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
        seen_count INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (alpha_id, check_name)
    );
    -- Alphas that missed submission by exactly one check. Re-simulating the
    -- same expression under different settings is a far better bet per
    -- simulation than a fresh random alpha — the idea is already known to pass
    -- 13-14 of the 15 checks — so the explore loop spends a small share of its
    -- batch budget re-running these instead of generating new ones.
    CREATE TABLE IF NOT EXISTS polish_candidates (
        alpha_id       TEXT PRIMARY KEY,
        expression     TEXT NOT NULL,
        region         TEXT NOT NULL,
        universe       TEXT NOT NULL,
        delay          INTEGER NOT NULL,
        neutralization TEXT,
        attempts       INTEGER NOT NULL DEFAULT 0,
        -- Comma-separated neutralizations already tried for this candidate.
        -- `variant_neutralization` excludes only the alpha's *original*
        -- neutralization, so without this a candidate could be re-run under one
        -- it had already been simulated with — an identical simulation, since
        -- the expression and cell are unchanged. Measured 2026-10-06/07: 50
        -- such repeats in a day, up to four times for one candidate.
        tried          TEXT NOT NULL DEFAULT '',
        created_at     TEXT NOT NULL
    );
    -- Finite, explicitly queued idea probes. The normal explorer owns their
    -- POSTs, polling and checks, so they obey its quota and concurrent slots.
    CREATE TABLE IF NOT EXISTS probe_batches (
        probe_id TEXT PRIMARY KEY,
        expressions TEXT NOT NULL,
        settings TEXT NOT NULL,
        template_tags TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'PENDING',
        parent_id TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL,
        claimed_at TEXT,
        retry_at DOUBLE NOT NULL DEFAULT 0
    );
"""

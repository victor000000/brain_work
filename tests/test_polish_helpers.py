"""Shared schema, fixtures and builders for the polish regression tests."""

import pytest

SCHEMA = """
CREATE TABLE alpha_results (
    alpha_id TEXT PRIMARY KEY, expression TEXT, region TEXT, universe TEXT,
    delay INTEGER, neutralization TEXT
);
CREATE TABLE submission_checks (
    alpha_id TEXT, check_name TEXT, result TEXT, limit_val TEXT, actual_val TEXT, extra TEXT,
    PRIMARY KEY (alpha_id, check_name)
);
CREATE TABLE alpha_check_summary (
    alpha_id TEXT PRIMARY KEY, pass_count INTEGER, fail_count INTEGER,
    warn_count INTEGER, pend_count INTEGER, checked_at TEXT
);
CREATE TABLE check_failures (
    alpha_id TEXT, check_name TEXT, limit_val TEXT, actual_val TEXT,
    first_seen TEXT, last_seen TEXT, seen_count INTEGER,
    PRIMARY KEY (alpha_id, check_name)
);
CREATE TABLE polish_candidates (
    alpha_id TEXT PRIMARY KEY, expression TEXT NOT NULL, region TEXT NOT NULL,
    universe TEXT NOT NULL, delay INTEGER NOT NULL, neutralization TEXT,
    attempts INTEGER NOT NULL DEFAULT 0, tried TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


@pytest.fixture
def conn():
    import duckdb

    c = duckdb.connect(":memory:")
    c.execute(SCHEMA)
    yield c
    c.close()


def _alpha(conn, aid="A1", region="HKG", uni="TOP800", delay=1, neut="SLOW", expr="rank(close)"):
    conn.execute("INSERT OR REPLACE INTO alpha_results VALUES (?,?,?,?,?,?)", (aid, expr, region, uni, delay, neut))


def _checks(n_pass, n_fail, n_pend=0):
    out = [{"name": f"P{i}", "result": "PASS", "limit": None, "value": None} for i in range(n_pass)]
    out += [{"name": f"F{i}", "result": "FAIL", "limit": 1.58, "value": 1.37} for i in range(n_fail)]
    out += [{"name": f"D{i}", "result": "PENDING", "limit": None, "value": None} for i in range(n_pend)]
    out += [{"name": "W0", "result": "WARNING", "limit": None, "value": None}]
    return out

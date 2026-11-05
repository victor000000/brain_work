"""Schema, timestamp and seed builders shared by the healthcheck test modules."""

from datetime import UTC, datetime, timedelta

import pytest

from core.db import connect


def _ts(delta):
    return (datetime.now(UTC) + delta).strftime("%Y-%m-%d %H:%M:%S UTC")


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript("""
        CREATE TABLE data_fields (
            id TEXT, category_id TEXT, dataset_id TEXT, region TEXT,
            delay INTEGER, universe TEXT,
            PRIMARY KEY (id, region, delay, universe)
        );
        CREATE TABLE datasets (
            id TEXT, name TEXT, category_id TEXT, region TEXT,
            delay INTEGER, universe TEXT,
            PRIMARY KEY (id, region, delay, universe)
        );
        CREATE TABLE dataset_categories (id TEXT PRIMARY KEY, name TEXT, parent_id TEXT);
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE alpha_results (
            alpha_id TEXT PRIMARY KEY, is_sharpe REAL, template TEXT, created_at TEXT
        );
        CREATE TABLE template_performance (template TEXT, region TEXT);
    """)
    yield c
    c.close()


def _seed_healthy(c, *, created_at=None, refresh_at=None, alphas=10, tracked=10):
    c.execute("INSERT INTO data_fields VALUES ('close', 'pv', 'pv1', 'USA', 1, 'TOP3000')")
    c.execute("INSERT INTO data_fields VALUES ('opt_iv', 'option', 'option8', 'USA', 1, 'TOP3000')")
    c.execute("INSERT INTO datasets VALUES ('pv1', 'Price', 'pv', 'USA', 1, 'TOP3000')")
    c.execute("INSERT INTO datasets VALUES ('option8', 'Options', 'option', 'USA', 1, 'TOP3000')")
    c.execute("INSERT INTO dataset_categories VALUES ('pv', 'Price', NULL)")
    c.execute("INSERT INTO dataset_categories VALUES ('pv-price-volume', 'Price Volume', 'pv')")
    c.execute("INSERT INTO dataset_categories VALUES ('option', 'Options', NULL)")
    c.execute("INSERT INTO metadata VALUES ('last_pv_option_refresh', ?)", (_ts(refresh_at or timedelta(0)),))
    now = created_at if created_at is not None else datetime.now(UTC).isoformat()
    c.executemany(
        "INSERT INTO alpha_results VALUES (?, 1.5, 'tpl', ?)",
        [(f"a{i}", now) for i in range(alphas)],
    )
    c.executemany("INSERT INTO template_performance VALUES ('tpl', 'USA')", [()] * tracked)
    c.commit()

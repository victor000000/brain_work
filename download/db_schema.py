"""Download DB schema and log helpers."""

import time

from core.db import connect


def init_db(db_path):
    conn = connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS dataset_categories (
            id TEXT PRIMARY KEY, name TEXT, parent_id TEXT,
            dataset_count INTEGER, field_count INTEGER,
            alpha_count INTEGER, user_count INTEGER,
            value_score REAL, regions TEXT, raw_json TEXT);
        CREATE TABLE IF NOT EXISTS data_fields (
            id TEXT, description TEXT, dataset_id TEXT, dataset_name TEXT,
            category_id TEXT, category_name TEXT,
            subcategory_id TEXT, subcategory_name TEXT,
            region TEXT, delay INTEGER, universe TEXT, type TEXT,
            date_coverage REAL, coverage REAL,
            user_count INTEGER, alpha_count INTEGER,
            pyramid_multiplier REAL, themes TEXT, raw_json TEXT,
            PRIMARY KEY (id, region, delay, universe));
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT, name TEXT, category_id TEXT, category_name TEXT,
            subcategory_id TEXT, subcategory_name TEXT,
            region TEXT, delay INTEGER, universe TEXT,
            PRIMARY KEY (id, region, delay, universe));
        CREATE TABLE IF NOT EXISTS download_log (
            region TEXT, universe TEXT, delay INTEGER,
            subcategory_id TEXT, field_count INTEGER, downloaded_at TEXT,
            PRIMARY KEY (region, universe, delay, subcategory_id));
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit()
    return conn


def is_downloaded(conn, region, universe, delay, subcat_id):
    return (
        conn.execute(
            "SELECT 1 FROM download_log WHERE region=? AND universe=? AND delay=? AND subcategory_id=?",
            (region, universe, delay, subcat_id),
        ).fetchone()
        is not None
    )


def mark_downloaded(conn, region, universe, delay, subcat_id, count):
    conn.execute(
        "INSERT OR REPLACE INTO download_log VALUES (?,?,?,?,?,?)",
        (region, universe, delay, subcat_id, count, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
    )
    conn.commit()

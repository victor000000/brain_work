"""In-memory schema, fixture and builders shared by the scope write-guard tests."""

import pytest

from core.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.execute("""
        CREATE TABLE dataset_categories (
            id TEXT PRIMARY KEY, name TEXT, parent_id TEXT, dataset_count INTEGER,
            field_count INTEGER, alpha_count INTEGER, user_count INTEGER,
            value_score REAL, regions TEXT, raw_json TEXT
        )
    """)
    c.execute("""
        CREATE TABLE data_fields (
            id TEXT, description TEXT, dataset_id TEXT, dataset_name TEXT,
            category_id TEXT, category_name TEXT, subcategory_id TEXT,
            subcategory_name TEXT, region TEXT, delay INTEGER, universe TEXT,
            type TEXT, date_coverage REAL, coverage REAL, user_count INTEGER,
            alpha_count INTEGER, pyramid_multiplier REAL, themes TEXT, raw_json TEXT,
            PRIMARY KEY (id, region, delay, universe)
        )
    """)
    c.execute("""
        CREATE TABLE datasets (
            id TEXT, name TEXT, category_id TEXT, category_name TEXT,
            subcategory_id TEXT, subcategory_name TEXT, region TEXT,
            delay INTEGER, universe TEXT,
            PRIMARY KEY (id, region, delay, universe)
        )
    """)
    return c


CATEGORIES = [
    {"id": "pv", "name": "Price Volume", "children": [{"id": "pv-price-volume", "name": "Price Volume"}]},
    {"id": "model", "name": "Model", "children": [{"id": "model-technical", "name": "Technical"}]},
    {"id": "option", "name": "Option", "children": []},
    {"id": "news", "name": "News", "children": []},
]


def field(fid, cat_id, dataset_id):
    return {
        "id": fid,
        "description": "",
        "type": "MATRIX",
        "region": "USA",
        "delay": 1,
        "universe": "TOP3000",
        "coverage": 1.0,
        "dateCoverage": 1.0,
        "dataset": {"id": dataset_id, "name": dataset_id},
        "category": {"id": cat_id, "name": cat_id},
        "subcategory": {"id": f"{cat_id}-sub", "name": "s"},
    }

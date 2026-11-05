"""Every in-scope dataset must reach the MATRIX pool.

`query_matrix_fields` applied one global `LIMIT 500` across all datasets. pv
holds ~88k fields and option ~619, and the pv field with the highest coverage
outranks every option field — so option datasets were crowded out entirely and
the generator never saw one. The restriction is pv *and* option; a pool that
contains only pv silently violates it.
"""

import pytest

from core.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.execute("""
        CREATE TABLE data_fields (
            id TEXT, dataset_id TEXT, category_id TEXT, region TEXT,
            delay INTEGER, universe TEXT, type TEXT,
            coverage REAL, date_coverage REAL, alpha_count INTEGER,
            description TEXT
        )
    """)
    c.execute("""
        CREATE TABLE field_blacklist (
            field_id TEXT, region TEXT, reason TEXT, PRIMARY KEY (field_id, region)
        )
    """)
    rows = []
    # A large, high-coverage pv dataset — the one that starved the rest.
    for i in range(4000):
        rows.append((f"pv_big_{i}", "pv1", "pv", "USA", 1, "TOP3000", "MATRIX", 1.0, 1.0, 100))
    # A small option dataset with slightly lower coverage.
    for i in range(30):
        rows.append((f"opt_{i}", "option8", "option", "USA", 1, "TOP3000", "MATRIX", 0.8, 0.8, 5))
    # A second, smaller pv dataset.
    for i in range(20):
        rows.append((f"pv_small_{i}", "pv13", "pv", "USA", 1, "TOP3000", "MATRIX", 0.7, 0.7, 3))
    c.executemany("INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)", rows)
    c.commit()
    return c


def test_small_datasets_are_not_starved(conn):
    from generator.field_queries_matrix import query_matrix_fields

    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "option8" in by_dataset, "option dataset crowded out by the global limit"
    assert "pv13" in by_dataset


def test_every_dataset_contributes_fields(conn):
    from generator.field_queries_matrix import query_matrix_fields

    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert set(by_dataset) == {"pv1", "option8", "pv13"}
    for ds, fields in by_dataset.items():
        assert fields, f"{ds} contributed no fields"


def test_the_large_dataset_is_capped_not_unbounded(conn):
    from generator.field_queries_matrix import query_matrix_fields

    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert len(by_dataset["pv1"]) <= 60, "per-dataset cap should bound the big dataset"


def test_category_map_covers_both_categories(conn):
    from generator.field_queries_matrix import query_matrix_fields

    _, dataset_to_category = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert set(dataset_to_category.values()) == {"pv", "option"}


def test_out_of_scope_datasets_are_still_excluded(conn):
    """Balancing must not widen the category filter."""
    from generator.field_queries_matrix import query_matrix_fields

    conn.execute(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        ("mdl_x", "mdl216", "model", "USA", 1, "TOP3000", "MATRIX", 1.0, 1.0, 99),
    )
    conn.commit()
    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "mdl216" not in by_dataset


def test_a_zero_coverage_field_with_use_evidence_is_kept(conn):
    """GBR and DEU report `coverage: 0.0` for `close` with `alphaCount` in the thousands.

    The metric is simply not populated in those regions, and `coverage >= 0.5`
    alone deleted their whole price pool — `close`, `vwap`, `high`, `low`,
    `open` and `adv20` — so four price templates and every volume template
    could not fire. `alpha_count > 0` is the evidence that replaces it.
    """
    from generator.field_queries_matrix import query_matrix_fields

    conn.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        [
            ("gb_close", "pvgb", "pv", "USA", 1, "TOP3000", "MATRIX", 0.0, 1.0, 4863),
            ("gb_never_used", "pvgb", "pv", "USA", 1, "TOP3000", "MATRIX", 0.0, 1.0, 0),
        ],
    )
    conn.commit()
    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "gb_close" in by_dataset.get("pvgb", [])


def test_a_zero_coverage_field_nobody_has_used_is_still_rejected(conn):
    """The rule is evidence, not an amnesty: no coverage and no use is no field."""
    from generator.field_queries_matrix import query_matrix_fields

    conn.execute(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        ("ghost", "pvghost", "pv", "USA", 1, "TOP3000", "MATRIX", 0.0, 1.0, 0),
    )
    conn.commit()
    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "pvghost" not in by_dataset


def test_a_covered_field_is_kept_whatever_its_use_count(conn):
    """Existing behaviour: real coverage admits a field no one has simulated yet."""
    from generator.field_queries_matrix import query_matrix_fields

    conn.execute(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        ("fresh", "pvfresh", "pv", "USA", 1, "TOP3000", "MATRIX", 0.9, 0.9, 0),
    )
    conn.commit()
    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "fresh" in by_dataset.get("pvfresh", [])


def test_identifier_fields_are_excluded_from_the_pool(conn):
    """`sedol` and `ticker` are identifiers, and ranking by one is not a signal.

    A stored expression shows what leaking them produces:
    `rank(group_neutralize(ts_delta(mdl313_companyname,63), sector) *
    rank(mdl313_ticker))` at sharpe 11.18. `isin` and `cusip` were already
    refused; these two were not, and both reach the pool as MATRIX fields.
    """
    from generator.field_queries_matrix import query_matrix_fields

    conn.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        [
            ("pv20_sedol", "pvid", "pv", "USA", 1, "TOP3000", "MATRIX", 0.9, 0.9, 5),
            ("pv37_adr_ticker_di", "pvid", "pv", "USA", 1, "TOP3000", "MATRIX", 0.9, 0.9, 5),
            ("pv1_close", "pvok", "pv", "USA", 1, "TOP3000", "MATRIX", 0.9, 0.9, 5),
        ],
    )
    conn.commit()
    by_dataset, _ = query_matrix_fields(conn, "USA", 1, "TOP3000")
    assert "pvid" not in by_dataset, "an identifier dataset reached the pool"
    assert "pv1_close" in by_dataset.get("pvok", [])

"""Every field loader must return price (pv) and options (option) data only.

Non-price categories (fundamental, model, news, analyst, other) are present in
the seed DB and must never reach the generator.
"""

from generator.field_queries import query_group_fields, query_vector_fields
from generator.field_queries_matrix import query_matrix_fields
from tests.test_category_filter.conftest import make_field_conn

REGION, DELAY, UNIVERSE = "USA", 0, "TOP3000"


def test_matrix_fields_load_only_price_and_options_datasets():
    """MATRIX pool is the expression input — fnd6/news12/model30 must be absent."""
    conn = make_field_conn()
    by_dataset, _ = query_matrix_fields(conn, REGION, DELAY, UNIVERSE)
    assert set(by_dataset) == {"pv1", "option8"}


def test_matrix_dataset_category_map_is_price_and_options_only():
    """dataset_to_category feeds pyramid targeting — no foreign categories."""
    conn = make_field_conn()
    _, dataset_to_category = query_matrix_fields(conn, REGION, DELAY, UNIVERSE)
    assert set(dataset_to_category.values()) <= {"pv", "option"}


def test_vector_fields_load_only_price_and_options():
    conn = make_field_conn()
    assert set(query_vector_fields(conn, REGION, DELAY, UNIVERSE)) == {"vec_pv", "vec_measure"}


def test_matrix_pool_excludes_metadata_fields():
    """A status code or a type is not a measurement.

    Both are MATRIX-typed in `data_fields` and carry a Group unit on the
    platform, so every series use is rejected. Measured live 2026-10-11: of the
    374 ten-expression batches containing one of the two, 373 failed all ten
    children, against 87 of 4,286 without.
    """
    conn = make_field_conn()
    by_dataset, _ = query_matrix_fields(conn, REGION, DELAY, UNIVERSE)
    loaded = {field for fields in by_dataset.values() for field in fields}
    assert "pv149_status_5" not in loaded
    assert "pv149_type_1" not in loaded
    assert "pv_measure" in loaded, "a measurement with the same dataset was dropped"


def test_vector_pool_excludes_labels_and_keeps_measurements():
    """The VECTOR loader had no label filter at all until 2026-10-11.

    VECTOR fields are read as series, never as partitions, so a label has no
    correct use in this pool — `pv20_category` ("Category classification") and
    `pv48_dynamic_es_cur` ("Pre-change economic sector classification code")
    were reaching the generator through this door.
    """
    conn = make_field_conn()
    loaded = set(query_vector_fields(conn, REGION, DELAY, UNIVERSE))
    assert "pv20_category" not in loaded
    assert "vec_measure" in loaded, "an ordinary VECTOR field was dropped with the labels"


def test_group_fields_load_only_price_and_options():
    """other455 holds ~29k GROUP fields on the live DB — it must not leak in."""
    conn = make_field_conn()
    assert set(query_group_fields(conn, REGION, DELAY, UNIVERSE)) == {"industry"}


def test_matrix_fields_ignore_the_field_blacklist():
    """All price/option fields are allowed — the blacklist table is not consulted.

    On the live DB this is what restores CHN/TOP2000U/d0, where 11 of 12 pv1
    fields carry a blacklist row.
    """
    conn = make_field_conn()
    by_dataset, _ = query_matrix_fields(conn, REGION, DELAY, UNIVERSE)
    loaded = {field for fields in by_dataset.values() for field in fields}
    assert {"cap", "close"} <= loaded, "blacklisted MATRIX fields were filtered out"


def test_vector_and_group_fields_ignore_the_field_blacklist():
    conn = make_field_conn()
    assert "vec_pv" in query_vector_fields(conn, REGION, DELAY, UNIVERSE)
    assert "industry" in query_group_fields(conn, REGION, DELAY, UNIVERSE)

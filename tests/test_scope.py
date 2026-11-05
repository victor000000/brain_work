"""The pv/option scope guard.

The restriction has to hold at write time. It was applied once as a cleanup
and did not survive the next refresh, which re-inserted 55 out-of-scope
categories.
"""

from core.scope import (
    ALLOWED_CATEGORIES,
    in_scope,
    keep_category,
    out_of_scope,
    scope_sql,
)


def test_top_level_allowed_categories():
    assert in_scope("pv")
    assert in_scope("option")


def test_child_categories_are_in_scope():
    """The platform names children `<parent>-<child>`."""
    assert in_scope("pv-price-volume")
    assert in_scope("pv-relationship")
    assert in_scope("option-option-analytics")


def test_foreign_categories_are_out_of_scope():
    for cat in ("model", "analyst", "fundamental", "news", "sentiment", "risk", "other"):
        assert out_of_scope(cat), cat


def test_lookalike_prefixes_are_not_matched():
    """`pvalue` and `options_x` must not pass on a naive prefix test."""
    assert out_of_scope("pvalue")
    assert out_of_scope("options-flow")
    assert out_of_scope("model-pv")


def test_missing_category_is_out_of_scope():
    for empty in (None, "", 0):
        assert out_of_scope(empty)


def test_keep_category_reads_a_row():
    assert keep_category({"id": "pv"})
    assert keep_category({"id": "pv13"}) is False  # not a category id form
    assert keep_category({"name": "pv"}, key="name")
    assert not keep_category({"id": "model"})


def test_scope_sql_matches_the_python_predicate():
    """The SQL and the Python check are built from one list — no drift."""
    sql = scope_sql("category_id")
    assert "category_id IN ('pv', 'option')" in sql
    assert "category_id LIKE 'pv-%'" in sql
    assert "category_id LIKE 'option-%'" in sql


def test_allowed_categories_is_the_single_source():
    assert ALLOWED_CATEGORIES == ("pv", "option")

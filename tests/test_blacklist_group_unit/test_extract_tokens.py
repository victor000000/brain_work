"""extract_field_tokens — set-intersection-based token extraction."""

from download.blacklist_group_unit import extract_field_tokens


def test_extract_field_tokens_simple():
    """Tokens that match the known field set are returned."""
    expr = "rank(foo + bar(baz, 21))"
    fields = {"foo", "bar", "baz", "unrelated"}
    assert extract_field_tokens(expr, fields) == {"foo", "bar", "baz"}


def test_extract_field_tokens_excludes_operators():
    """Operator names like 'rank' are excluded by the field-set intersection."""
    expr = "rank(ts_zscore(price, 60))"
    fields = {"price"}
    assert extract_field_tokens(expr, fields) == {"price"}


def test_extract_field_tokens_handles_nested():
    """Deeply nested expressions extract every distinct field."""
    expr = "rank((rank(foo) / (1 + days_from_last_change(bar))) * baz)"
    fields = {"foo", "bar", "baz"}
    assert extract_field_tokens(expr, fields) == {"foo", "bar", "baz"}


def test_extract_field_tokens_ignores_short_tokens():
    """Numeric literals never match real field IDs (set intersection filters them)."""
    expr = "rank(foo / (a + 0.01))"
    fields = {"foo"}
    assert extract_field_tokens(expr, fields) == {"foo"}


def test_extract_field_tokens_empty_expression():
    """Empty or None expression returns empty set, no exception."""
    assert extract_field_tokens("", {"foo"}) == set()
    assert extract_field_tokens(None, {"foo"}) == set()

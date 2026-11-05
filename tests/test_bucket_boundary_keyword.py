"""Explicit native bucket boundaries must not masquerade as a field."""

from generator.template_fill import filled_expression_problem, unknown_field_tokens


def test_explicit_boundaries_pass_full_expression_validation():
    expression = "group_rank(close, bucket(rank(close), buckets='0.2,0.4,0.6,0.8'))"
    assert filled_expression_problem(expression, {"close"}, {"group_rank", "bucket", "rank"}, set(), set()) is None


def test_bare_buckets_and_unknown_values_still_require_field_validation():
    assert unknown_field_tokens("rank(buckets)", {"close"}) == {"buckets"}
    assert unknown_field_tokens("bucket(rank(unknown), buckets='0.2,0.8')", {"close"}) == {"unknown"}

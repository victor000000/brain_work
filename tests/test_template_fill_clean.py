"""Stripping corpus prose down to the parseable formula (clean_skeleton)."""

from generator.template_fill import clean_skeleton
from tests.test_template_fill_helpers import OPS


def test_clean_skeleton_strips_prose_around_the_formula():
    """The corpus wraps real expressions in prose; the call is the skeleton."""
    assert clean_skeleton("排序成交量：rank({f})对当日的成交量进行排序。", OPS) == "rank({f})"  # noqa: RUF001
    assert clean_skeleton("rank({f}):对当天的成交量进行横截面排名。", OPS) == "rank({f})"
    assert clean_skeleton("sort by volume: ts_rank({f},10)", OPS) == "ts_rank({f},10)"
    # A cut-off trailing operator is not part of the expression.
    assert clean_skeleton("ts_delta({f},5)/", OPS) == "ts_delta({f},5)"


def test_clean_skeleton_strips_assignment_prefixes():
    """One-line templates were written as `name = expression`."""
    assert clean_skeleton("组件A = ts_rank({f},10)", OPS) == "ts_rank({f},10)"
    assert clean_skeleton("alpha = ts_delta({f},5)", OPS) == "ts_delta({f},5)"


def test_clean_skeleton_keeps_valid_skeletons_unchanged():
    for skeleton in ["ts_rank({f},20)", "rank(close)", "ts_delta(x,d)"]:
        assert clean_skeleton(skeleton, OPS) == skeleton


def test_clean_skeleton_returns_the_input_or_a_parseable_substring():
    """No parseable core means no change, and anything returned is contained.

    Cleaning must not invent an expression — the result is either the input or
    a contiguous substring of it (as with a wrapper whose arguments hold the
    only standalone-valid form, `{f}=bucket(rank({f}),...)` → `rank({f})`).
    """
    garbage = "no expression here at all"
    assert clean_skeleton(garbage, OPS) == garbage

    bucket = "{f}=bucket(rank({f}),range='0,1,0.1')"
    cleaned = clean_skeleton(bucket, OPS)
    assert cleaned in bucket

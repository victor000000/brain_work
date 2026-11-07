"""Semantic scope validation (design 2026-11-05, P0-1).

The category guard answers "was this dataset in scope?"; these answer "does
every numeric leaf of THIS expression resolve to a permitted measurement?".
The distinction matters because a field can come from an in-scope dataset and
still be a classifier code, or a partition used as a number.
"""

from core.scope import (
    classify_leaf,
    dispatch_block_reason,
    expression_leaves,
    validate_expression,
)


def test_operators_are_not_data_leaves():
    leaves = expression_leaves("rank(ts_mean(close, 20) / ts_std_dev(returns, 60))")
    assert leaves == ["close", "returns"], leaves


def test_a_pure_pv_expression_is_ok():
    v = validate_expression("rank((close - vwap) / vwap)")
    assert v["status"] == "ok", v
    assert dispatch_block_reason(v) is None


def test_option_plus_pv_is_ok():
    v = validate_expression("rank(opt3_volcallotma - opt3_volputotma) + rank(close)")
    assert v["status"] == "ok", v
    assert set(v["permitted"]) == {"opt3_volcallotma", "opt3_volputotma", "close"}


def test_risk_input_is_a_violation():
    """O0Aoneaq shipped with this family; a compliant set must refuse it."""
    v = validate_expression("rank(1.0 / ts_std_dev(idiosyncratic_return_fraction, 250))")
    assert v["status"] == "violation", v
    assert "idiosyncratic_return_fraction" in v["blocked"]
    assert "out-of-scope" in dispatch_block_reason(v)


def test_analyst_input_is_a_violation():
    v = validate_expression("rank(ts_mean(anl4_adxqfv110_mean, 20))")
    assert v["status"] == "violation", v
    assert "anl4_adxqfv110_mean" in v["blocked"]


def test_a_partition_used_as_a_number_is_a_violation():
    """GROUP leaves may only appear as partitions, never as numeric inputs."""
    v = validate_expression(
        "rank(close) + rank(sector_code)",
        resolver=lambda leaf: "group" if leaf == "sector_code" else classify_leaf(leaf),
    )
    assert v["status"] == "violation", v
    assert "sector_code" in v["blocked"]


def test_an_unresolvable_leaf_requires_review_not_permission():
    v = validate_expression("rank(mystery_field_zz)")
    assert v["status"] == "review", v
    assert "mystery_field_zz" in v["unresolved"]
    assert "review" in dispatch_block_reason(v)


def test_an_expression_with_no_resolvable_leaf_is_review():
    v = validate_expression("1 + 2")
    assert v["status"] == "review", v


def test_blocked_wins_over_unresolved():
    v = validate_expression("rank(idiosyncratic_return_fraction) + rank(mystery_field_zz)")
    assert v["status"] == "violation", v

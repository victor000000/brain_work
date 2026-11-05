"""Test template tracking and identification."""

from storage.track_templates import identify_template


def test_identify_regression():
    """Raw ts_regression (no zscore preprocessing) maps to raw_regression — the
    more specific signature is matched ahead of generic trend_strength."""
    expr = "rank(ts_regression(field1, field2, 42))"
    assert identify_template(expr) == "raw_regression"


def test_identify_power():
    expr = "rank(signed_power(rank(field1) - rank(field2), 0.5))"
    assert identify_template(expr) == "power_scaling"


def test_identify_group():
    expr = "rank(group_rank(field1, sector) * rank(field2))"
    assert identify_template(expr) == "peer_rank"


def test_identify_ternary():
    expr = "rank((ts_delta(field1,21) > 0) ? rank(field2) : -rank(field2))"
    assert identify_template(expr) == "ternary_regime"


def test_identify_staleness():
    expr = "rank(days_from_last_change(field1) * rank(field2))"
    assert identify_template(expr) == "staleness_alpha"


def test_identify_unknown():
    expr = "completely_unknown_expression"
    assert identify_template(expr) == "unknown"


def test_identify_vec():
    expr = "rank(field1 * vec_avg(vector_field))"
    assert identify_template(expr) == "vec_avg"


def test_identify_bucket():
    expr = 'bucket(rank(field2), range="0,1,0.2")'
    assert identify_template(expr) == "bucket"

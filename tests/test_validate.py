"""Local expression validation via py-fastplus."""

from generator.validate import is_valid, parse_error, validate_batch


def test_valid_expression_passes():
    assert is_valid("rank(ts_delta(close, 5))")


def test_valid_group_expression_passes():
    assert is_valid("group_neutralize(rank(close), sector)")


def test_syntax_error_is_rejected():
    assert not is_valid("rank(close")
    assert not is_valid("")
    assert not is_valid("rank(close))")


def test_group_mean_arity_is_enforced():
    """BRAIN's group_mean takes (value, weight, group) — a real forum mistake."""
    assert is_valid("group_mean(close, 1, sector)")
    assert not is_valid("group_mean(close, sector)")


def test_signal_may_not_be_a_group():
    """A final signal must be matrix-compatible, not a Group."""
    assert not is_valid("bucket(rank(close), range='0,1,0.1')")


def test_parse_error_returns_message_for_bad_input():
    assert parse_error("rank(close") is not None
    assert parse_error("rank(close)") is None


def test_validate_batch_splits_valid_from_invalid():
    good, bad = validate_batch(["rank(close)", "rank(close", "ts_rank(close, 20)"])
    assert good == ["rank(close)", "ts_rank(close, 20)"]
    assert bad == ["rank(close"]

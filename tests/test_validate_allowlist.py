"""The operator allowlist, and the parser rules fastplus is too permissive on.

fastplus treats an unknown identifier followed by `(` as a generic function
call, so it accepts `totally_made_up_operator(close)` and `adv20(close)` — the
latter being a *field* used as a function. Syntax alone is too weak for
generated text, so callers can pass the platform's operator list.

Split out of `tests/test_validate.py`; the syntax/type tests stay there.
"""

from generator.validate import called_identifiers, is_valid, parse_error
from tests.conftest import open_prod_db

OPS = {"rank", "ts_delta", "ts_rank", "group_rank", "zscore", "ts_mean", "close"}


def test_known_operators_pass_the_allowlist():
    assert is_valid("rank(ts_delta(close, 5))", known_operators=OPS)


def test_unknown_operator_is_rejected():
    assert not is_valid("totally_made_up_operator(close)", known_operators=OPS)
    assert parse_error("totally_made_up_operator(close)", known_operators=OPS)


def test_field_used_as_a_function_is_rejected():
    """`adv20` is a field; calling it is the classic mined-corpus artifact."""
    assert not is_valid("adv20(zscore(close))", known_operators=OPS)
    assert is_valid("adv20", known_operators=OPS)


def test_allowlist_accepts_a_real_expression():
    assert is_valid(
        "group_rank(ts_rank(close,63),sector)",
        known_operators={"group_rank", "ts_rank", "close", "sector"},
    )


def test_without_an_allowlist_behaviour_is_unchanged():
    """Syntax-only mode stays available for callers that have no operator list."""
    assert is_valid("totally_made_up_operator(close)")


def test_operator_names_load_from_the_database():
    from generator.validate import load_operator_names

    ops = load_operator_names(open_prod_db())
    assert "rank" in ops and "ts_delta" in ops
    assert len(ops) > 50


def test_leading_plus_is_rejected():
    """fastplus accepts a leading unary '+', the platform parser rejects it
    (`Unexpected character '+'`) — every one submitted burns a simulation."""
    assert parse_error("+0.2*rank(-ts_delta(close,3))") is not None
    assert parse_error("  +0.3*rank(close)") is not None
    assert parse_error("-0.2*rank(close)") is None  # unary minus is fine


def test_logical_operators_are_visible_to_the_allowlist():
    """`and`/`or`/`not` are operators, not syntax — the platform's table says so.

    Category Logical, defined as `and(input1, input2)`; Fast Expression has no
    infix form. They sat in `_NOT_OPERATORS` as "syntax", which made a logical
    call invisible to this allowlist — `and(...)` could call anything without
    `and` being a known operator — and invisible to the template tag check in
    `tests/test_templates_operators.py`. Found 2026-10-12, when a new template
    declared `and` in its tag and that check reported it as never emitted.
    """
    assert called_identifiers("and(close > 1, rank(close) > 0.5)") == {"and", "rank"}
    assert not is_valid("and(close, close)", known_operators=OPS)
    assert is_valid("and(close > 1, close > 0)", known_operators=OPS | {"and"})

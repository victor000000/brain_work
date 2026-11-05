"""Test the random alpha generator end-to-end."""

from generator.random_generator import generate_expressions
from generator.validate import load_operator_names, parse_error
from tests.conftest import open_prod_db


def test_generate_basic():
    """Every generated expression must parse and use real operators.

    Asserted with py-fastplus plus the platform's operator allowlist rather
    than by substring-matching a hardcoded operator list: templates mined from
    the forum legitimately produce operator mixes outside any fixed list, so
    substring matching both under- and over-rejects.
    """
    conn = open_prod_db()
    exprs = generate_expressions(conn, "USA", 1, "TOP3000", 5)
    assert len(exprs) == 5, f"Expected 5, got {len(exprs)}"

    operators = load_operator_names(conn)
    for expr in exprs:
        assert isinstance(expr, str)
        assert expr.strip(), "Generated an empty expression"
        problem = parse_error(expr, operators)
        assert problem is None, f"{expr}\n  -> {problem}"


def test_generate_all_regions():
    """Generate at least 1 expression for each region config."""
    from core.regions import REGION_CONFIGS

    conn = open_prod_db()
    failed = []
    for region, universe, delay in REGION_CONFIGS:
        exprs = generate_expressions(conn, region, delay, universe, 2)
        if len(exprs) < 1:
            failed.append(f"{region}/{universe}/d{delay}")

    assert not failed, f"Failed to generate for: {failed}"


def test_no_duplicate_expressions():
    """Generated expressions should be unique."""
    conn = open_prod_db()
    exprs = generate_expressions(conn, "USA", 1, "TOP3000", 10)
    assert len(exprs) == len(set(exprs)), "Duplicate expressions generated"


def test_expressions_have_balanced_parens():
    """All generated expressions should have balanced parentheses."""
    conn = open_prod_db()
    exprs = generate_expressions(conn, "EUR", 1, "TOP2500", 5)
    for expr in exprs:
        assert expr.count("(") == expr.count(")"), f"Unbalanced: {expr[:80]}"


def test_invented_operator_never_reaches_output(monkeypatch):
    """The built-in path is not self-validating; the batch-level check is the
    only thing standing between a broken template and a wasted simulation."""
    from generator import template_source

    conn = open_prod_db()
    monkeypatch.setattr(template_source, "template_mix", lambda: 1.0)
    monkeypatch.setattr(template_source, "next_expression", lambda *a, **k: "totally_made_up_operator(close)")
    exprs = generate_expressions(conn, "USA", 1, "TOP3000", 5)
    assert len(exprs) == 5, "invalid templates must not starve the batch"
    assert not any("totally_made_up_operator" in e for e in exprs)
    operators = load_operator_names(conn)
    for expr in exprs:
        assert parse_error(expr, operators) is None, expr

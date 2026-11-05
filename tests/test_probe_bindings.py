"""Probe bindings must preserve scope/type gates while sharing calculations."""

import pytest

from runner import probe_validation
from runner.probe_bindings import validation_expressions
from runner.settings_factory import make_settings


def validate(monkeypatch, expression):
    monkeypatch.setattr(probe_validation, "target_pools", lambda *a: ({"close", "volume"}, set(), {"industry"}))
    monkeypatch.setattr(probe_validation, "load_operator_names", lambda *a: {"rank", "group_rank", "vec_avg"})
    settings = make_settings("USA", "TOP3000", 1, neutralization="MARKET", decay=0, truncation=0.08)
    probe_validation.validate_probe(None, [expression], settings, ["binding:test"])


def test_sequential_bindings_preserve_expression(monkeypatch):
    text = "base = close / volume; score = rank(base); rank(score)"
    validate(monkeypatch, text)
    assert validation_expressions(text, {"close", "volume", "rank"})[-1] == "rank((rank((close / volume))))"


@pytest.mark.parametrize(
    "expression",
    [
        "a = sales; rank(a)",
        "a = b; b = close; rank(a)",
        "a = a + close; rank(a)",
        "close = volume; rank(close)",
        "a = close; a = volume; rank(a)",
        "a = close; rank(volume)",
        "a = close; vec_avg(a)",
        "a = close; group_rank(volume,a)",
        "a = industry; rank(a)",
    ],
)
def test_invalid_bindings_cannot_launder_fields_or_types(monkeypatch, expression):
    with pytest.raises(ValueError):
        validate(monkeypatch, expression)


def test_quoted_semicolon_is_not_a_statement_separator():
    assert validation_expressions("a = close; f(a, 'a;b')", {"close"})[-1] == "f(close, 'a;b')"

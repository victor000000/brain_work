"""Per-cell sign exploration for a region whose signals arrive inverted."""

import random

import pytest

from generator import sign_policy as sp
from generator.weighted_selection import record_expr_template


class _Conn:
    """Minimal stand-in for the compat connection: one canned result set."""

    def __init__(self, rows, raises=None):
        self._rows = rows
        self._raises = raises

    def execute(self, sql, params=()):
        if self._raises:
            raise self._raises
        return _Cursor(self._rows)


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.fixture(autouse=True)
def _clean_policy(monkeypatch):
    """Every test starts from a cleared policy and the default env.

    The expression->template map is process-global and shared with every other
    test module, so it is snapshotted and restored rather than cleared: a test
    that clears it would break whichever module recorded into it first.
    """
    from generator.weighted_selection.state import get_state

    monkeypatch.delenv("BRAIN_SIGN_FLIP", raising=False)
    monkeypatch.delenv("BRAIN_SIGN_FLIP_MIX", raising=False)
    sp._policy.clear()
    sp._measured.clear()
    saved = dict(get_state().expr_templates)
    yield
    sp._policy.clear()
    sp._measured.clear()
    get_state().expr_templates.clear()
    get_state().expr_templates.update(saved)


def test_an_inverted_cell_gets_the_flip_probability():
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    assert sp.negation_probability("CHN") == sp.DEFAULT_FLIP_MIX
    assert sp.measured("CHN") == (9000, -0.93)


def test_a_normal_cell_stays_untouched():
    """Every region but CHN sits within +-0.2 of zero; none may be flipped."""
    sp.load_sign_policy(_Conn([("HKG", 25000, 0.08), ("USA", 37000, 0.04), ("EUR", 77000, 0.07)]))
    for region in ("HKG", "USA", "EUR"):
        assert sp.negation_probability(region) == 0.0


def test_a_thin_cell_is_not_judged():
    """Below the sample bar the cell behaves exactly as it did before."""
    sp.load_sign_policy(_Conn([("KOR", 499, -2.0)]))
    assert sp.negation_probability("KOR") == 0.0
    assert sp.measured("KOR") == (499, -2.0)


def test_the_policy_can_be_disabled(monkeypatch):
    monkeypatch.setenv("BRAIN_SIGN_FLIP", "0")
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    assert sp.negation_probability("CHN") == 0.0


def test_the_mix_is_overridable(monkeypatch):
    monkeypatch.setenv("BRAIN_SIGN_FLIP_MIX", "1.0")
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    assert sp.negation_probability("CHN") == 1.0


def test_a_bad_mix_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("BRAIN_SIGN_FLIP_MIX", "not-a-number")
    assert sp.flip_mix() == sp.DEFAULT_FLIP_MIX


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_a_nonfinite_mix_cannot_change_the_orientation_policy(value, monkeypatch):
    monkeypatch.setenv("BRAIN_SIGN_FLIP_MIX", value)
    assert sp.flip_mix() == sp.DEFAULT_FLIP_MIX


def test_a_missing_table_leaves_the_policy_off():
    """Generation must not stop because the outcome table is unreadable."""
    sp.load_sign_policy(_Conn(None, raises=RuntimeError("no such table")))
    assert sp.negation_probability("CHN") == 0.0


def test_an_unjudged_region_is_never_negated():
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    rng = random.Random(1)
    for _ in range(50):
        assert sp.maybe_negate("rank(close)", rng, "USA") == "rank(close)"


def test_negation_flips_and_is_wrapped():
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    sp._policy["CHN"] = 1.0
    assert sp.maybe_negate("rank(close) + rank(volume)", random.Random(1), "CHN") == "-(rank(close) + rank(volume))"


def test_an_already_negative_expression_negates_cleanly():
    """`-(-x)` is sound, so a template that already emits a minus still flips."""
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    sp._policy["CHN"] = 1.0
    assert sp.maybe_negate("-rank(close)", random.Random(1), "CHN") == "-(-rank(close))"


def test_provenance_follows_the_negated_string():
    """Storage reads the map back by expression string, so the key must be *added*.

    Without the negated key the alpha is stored under the name nothing weights
    — the 2026-10-08 `unknown` defect.

    The key is added, not moved. This test used to assert
    `lookup_expr_template("rank(close)") is None`, requiring the base entry to
    be consumed; that conflated "the negated key must exist" with "the base key
    must be gone", and it pinned the consuming read that cost the attribution
    of every later draw of a repeated string.
    """
    from generator.weighted_selection import peek_expr_template

    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    sp._policy["CHN"] = 1.0
    record_expr_template("rank(close)", "pool:proven")
    out = sp.maybe_negate("rank(close)", random.Random(1), "CHN")
    assert out == "-(rank(close))"
    assert peek_expr_template(out) == "pool:proven"
    assert peek_expr_template("rank(close)") == "pool:proven"


def test_the_flip_rate_matches_the_probability():
    sp.load_sign_policy(_Conn([("CHN", 9000, -0.93)]))
    sp._policy["CHN"] = 0.5
    rng = random.Random(4)
    flipped = sum(1 for _ in range(2000) if sp.maybe_negate("rank(close)", rng, "CHN").startswith("-("))
    assert 900 < flipped < 1100, flipped


def test_negation_does_not_consume_the_provenance_entry():
    """`peek`, not `lookup` — the map is keyed by a string templates repeat.

    A slotless template emits the same expression on every draw, so a
    consuming read attributes the first one and leaves every later draw to the
    regex fallback, which has no pattern for pure arithmetic: they were stored
    as `unknown`, the name nothing weights. Measured 2026-10-10 on CHN, where
    `(close - vwap) / vwap` is `vwap_close_spread` on every single draw.
    """
    from generator.weighted_selection import peek_expr_template

    sp._policy["CHN"] = 1.0  # flip always, so the outcome is deterministic
    for i in range(3):
        record_expr_template("(close - vwap) / vwap", "vwap_close_spread")
        assert sp.maybe_negate("(close - vwap) / vwap", random.Random(i), "CHN") == "-((close - vwap) / vwap)"
        assert peek_expr_template("-((close - vwap) / vwap)") == "vwap_close_spread"


def test_the_base_expression_keeps_its_provenance_after_a_flip():
    """Consuming the base entry also lost the *unflipped* draws of that string."""
    from generator.weighted_selection import peek_expr_template

    record_expr_template("(high - low) / close", "high_low_spread")
    sp._policy["CHN"] = 1.0
    sp.maybe_negate("(high - low) / close", random.Random(2), "CHN")
    assert peek_expr_template("(high - low) / close") == "high_low_spread"

"""Multi-field build helpers: releasing discarded halves from expr_templates."""

import generator.random_generator_build as rb
import generator.weighted_selection as ws


def test_make_4field_releases_intermediate_tracking(monkeypatch):
    """Discarded halves must not stay in expr_templates (unbounded growth)."""
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        seq = iter(["rank(close)", "rank(close)", "rank(close)", "rank(volume)"])

        def stub(cell_context=None):
            expr = next(seq, None)
            ws.record_expr_template(expr, "half")
            return expr

        monkeypatch.setattr(rb, "_make_2field_expression", stub)
        expr = rb._make_4field()
        assert expr is not None
        # Only the combo itself remains; both halves were consumed.
        assert len(fresh.expr_templates) == 1
        assert ws.lookup_expr_template("rank(close)") is None
        assert ws.lookup_expr_template("rank(volume)") is None
        assert fresh.expr_templates.get(expr, "").startswith("combo_")
    finally:
        ws.set_state(ws.UsageState())


def test_make_4field_release_is_idempotent_for_identical_halves(monkeypatch):
    """A discarded pair of identical halves must not leak its entry either."""
    fresh = ws.UsageState()
    ws.set_state(fresh)
    try:
        seq = iter(["rank(close)"] * 10)

        def stub(cell_context=None):
            expr = next(seq, None)
            ws.record_expr_template(expr, "half")
            return expr

        monkeypatch.setattr(rb, "_make_2field_expression", stub)
        assert rb._make_4field() is None
        assert fresh.expr_templates == {}
    finally:
        ws.set_state(ws.UsageState())

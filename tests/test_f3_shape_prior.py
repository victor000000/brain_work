"""Tests for P6 shape_prior — per-template forward-compatibility safety rail."""


def test_known_template_returns_one():
    """Known templates (all 0/1/2-window) get full weight 1.0."""
    from generator.shape_prior import shape_weight

    assert shape_weight("power_ratio") == 1.0
    assert shape_weight("scale_rank_zscore") == 1.0
    assert shape_weight("combo_4f_diff") == 1.0


def test_unknown_template_defaults_to_one():
    """Forward-compat: future templates not in the table get neutral weight 1.0."""
    from generator.shape_prior import shape_weight

    assert shape_weight("future_template") == 1.0
    assert shape_weight("") == 1.0


def test_explicit_zero_weight_template(monkeypatch):
    """A future ≥3-window template can be explicitly tagged 0.0 to gate it."""
    import generator.shape_prior as sp

    monkeypatch.setitem(sp._SHAPE_WEIGHTS, "risky_combo", 0.0)
    assert sp.shape_weight("risky_combo") == 0.0

"""Multi-field build helpers: degenerate-half redraws and the field pool."""

import generator.random_generator_build as rb


def _stub_picker(monkeypatch, values):
    """Return `values` in order from `_make_2field_expression`."""
    seq = iter(values)

    def stub(cell_context=None):
        return next(seq, None)

    monkeypatch.setattr(rb, "_make_2field_expression", stub)


def test_make_4field_redraws_identical_halves(monkeypatch):
    """rank(X - X) is identically zero: the first draw (x, x) must be redrawn."""
    _stub_picker(monkeypatch, ["x", "x", "x", "y"])
    expr = rb._make_4field()
    assert expr is not None
    assert "x" in expr and "y" in expr


def test_make_4field_gives_up_when_halves_never_differ(monkeypatch):
    _stub_picker(monkeypatch, ["x"] * 10)
    assert rb._make_4field() is None


def test_make_5field_redraws_identical_halves(monkeypatch):
    _stub_picker(monkeypatch, ["x", "x", "x", "y"])
    monkeypatch.setattr(rb, "pick_matrix", lambda count=1: ["z"])
    expr = rb._make_5field()
    assert expr is not None
    assert "x" in expr and "y" in expr and "z" in expr


def test_make_5field_gives_up_when_halves_never_differ(monkeypatch):
    _stub_picker(monkeypatch, ["x"] * 10)
    monkeypatch.setattr(rb, "pick_matrix", lambda count=1: ["z"])
    assert rb._make_5field() is None


def test_field_pool_tracks_reloaded_fields(monkeypatch):
    """A new region's fields must replace the cached pool.

    `load_all_fields` rebinds `matrix_by_dataset` on the module-singleton
    cache, so keying the memo on the cache's own identity would keep the first
    region's fields (and emit them in every later region) for the whole run.
    """
    import generator.field_picker.cache as cache_mod

    fresh = cache_mod.FieldCache()
    fresh.matrix_by_dataset = {"pv1": ["close", "volume"]}
    monkeypatch.setattr(cache_mod, "_cache", fresh)
    assert rb._field_pool() == ["close", "volume"]

    # Same cache object, new dict — exactly what a region change does.
    fresh.matrix_by_dataset = {"pv2": ["pcr_oi_180"]}
    assert rb._field_pool() == ["pcr_oi_180"]

"""Tests for P3 alpha-pyramid attribution — pure-function derivation."""


def test_derive_single_category():
    """Single-category alpha returns a 1-element JSON array."""
    from storage.track_pyramid import derive_pyramid_categories

    fmap = {"foo_pv": "pv", "bar_pv": "pv"}
    assert derive_pyramid_categories("rank(foo_pv + bar_pv)", fmap) == '["pv"]'


def test_derive_multi_category_sorted():
    """Multi-category alpha returns alphabetically-sorted JSON regardless of token order."""
    from storage.track_pyramid import derive_pyramid_categories

    fmap = {"foo_pv": "pv", "bar_risk": "risk", "baz_analyst": "analyst"}
    result = derive_pyramid_categories("rank(bar_risk + foo_pv + baz_analyst)", fmap)
    assert result == '["analyst","pv","risk"]'


def test_derive_filters_unknown_tokens():
    """Operator names and integer literals don't appear in field_to_category, so
    they're filtered by the set intersection."""
    from storage.track_pyramid import derive_pyramid_categories

    fmap = {"foo_pv": "pv"}
    assert derive_pyramid_categories("rank(ts_zscore(foo_pv, 21))", fmap) == '["pv"]'


def test_derive_empty_or_none():
    """Empty/None expression returns None (not '[]')."""
    from storage.track_pyramid import derive_pyramid_categories

    fmap = {"foo_pv": "pv"}
    assert derive_pyramid_categories(None, fmap) is None
    assert derive_pyramid_categories("", fmap) is None


def test_derive_no_recognizable_fields_returns_none():
    """An expression where nothing resolves returns None, not '[]'.

    Preserves the difference between 'we tried and matched nothing' (None)
    and 'parsed an empty list' (which never happens by construction).
    """
    from storage.track_pyramid import derive_pyramid_categories

    fmap = {"foo_pv": "pv"}
    assert derive_pyramid_categories("rank(unknown_token + 21)", fmap) is None

"""pick_matrix must always return `count` fields when the pool can supply them.

Regression: a pool holding a single dataset fell through to pick_cross_dataset,
which returns [] when len(dataset_ids) < 2 — instead of falling back to
pick_same_dataset. Affects MEA/TOP300/d1 (2 fields, one dataset), which flaked
roughly 1 run in 20.
"""

import pytest

from generator.field_picker import FieldCache, set_cache
from generator.field_picker_matrix import pick_matrix
from generator.field_picker_matrix.target import set_target_category


@pytest.fixture
def cache():
    """Install a FieldCache for the test, then restore an empty one."""

    def _category_of(dataset_id):
        """Mirror BRAIN's naming: option* datasets are category 'option'."""
        return "option" if dataset_id.startswith("option") else "pv"

    def _install(matrix_by_dataset, dataset_to_category=None):
        c = FieldCache()
        c.matrix_by_dataset = matrix_by_dataset
        c.dataset_to_category = dataset_to_category or {ds: _category_of(ds) for ds in matrix_by_dataset}
        c.rebuild_category_index()
        set_cache(c)
        return c

    set_target_category(None)
    yield _install
    set_cache(FieldCache())
    set_target_category(None)


def test_single_dataset_pool_always_yields_count_fields(cache):
    """200 draws: the cross-dataset branch (10% of calls) must still fall back."""
    cache({"pv1": ["close", "open", "high", "low", "volume"]})
    for i in range(200):
        picked = pick_matrix(count=2)
        assert len(picked) == 2, f"draw {i} returned {picked}"


def test_single_dataset_pool_exactly_at_count(cache):
    """The MEA/TOP300/d1 shape — exactly 2 fields in 1 dataset."""
    cache({"pv1": ["close", "open"]})
    for i in range(200):
        picked = pick_matrix(count=2)
        assert len(picked) == 2, f"draw {i} returned {picked}"


def test_multi_dataset_pool_still_works(cache):
    """The cross-dataset path must stay reachable when it can succeed."""
    cache({"pv1": ["close", "open", "high"], "option8": ["iv", "skew", "vol"]})
    for i in range(100):
        picked = pick_matrix(count=2)
        assert len(picked) == 2, f"draw {i} returned {picked}"


def test_target_category_still_honoured(cache):
    """Target selection must keep working after the fallback change."""
    cache({"pv1": ["close", "open", "high"], "option8": ["iv", "skew", "vol"]})
    set_target_category("option")
    for _ in range(50):
        picked = pick_matrix(count=2)
        assert len(picked) == 2
        assert any(f in {"iv", "skew", "vol"} for f in picked), picked


def test_pool_too_small_returns_what_it_can(cache):
    """A pool that genuinely cannot supply `count` must not raise."""
    cache({"pv1": ["close"]})
    picked = pick_matrix(count=2)
    assert picked == []

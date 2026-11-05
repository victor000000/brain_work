"""F6 cache-holder tests for FieldCache — reset + singleton swap."""

import pytest

import generator.field_picker as fp
from core.db import OperationalError


def test_field_cache_reset():
    cache = fp.FieldCache()
    cache.matrix_by_dataset = {"ds1": ["f1", "f2"]}
    cache.vector_fields = ["v1"]
    cache.group_fields = ["g1"]
    cache.last_loaded = ("USA", 1, "TOP3000")
    cache.reset()
    assert cache.matrix_by_dataset == {}
    assert cache.vector_fields == []
    assert cache.group_fields == []
    assert cache.last_loaded is None


def test_field_cache_set_swaps_singleton():
    original = fp.get_cache()
    fresh = fp.FieldCache()
    fresh.matrix_by_dataset = {"ds_test": ["f_test"]}
    fp.set_cache(fresh)
    try:
        assert fp.get_cache() is fresh
        assert "ds_test" in fp.get_cache().matrix_by_dataset
    finally:
        fp.set_cache(original)


def test_failed_load_does_not_poison_the_cache(monkeypatch):
    """A transient query error must not cache an empty pool for the process
    lifetime — the load marker is set only after every loader returns."""
    from generator.field_picker import loader

    calls = {"n": 0}

    def flaky(conn, region, delay, universe):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("database is locked")
        return {"ds1": ["close"]}, {"ds1": "pv"}

    monkeypatch.setattr(loader, "query_matrix_fields", flaky)
    monkeypatch.setattr(loader, "query_vector_fields", lambda *a: [])
    monkeypatch.setattr(loader, "query_group_fields", lambda *a: [])

    original = fp.get_cache()
    fp.set_cache(fp.FieldCache())
    try:
        with pytest.raises(OperationalError):
            loader.load_all_fields(None, "USA", 0, "TOP3000")
        assert fp.get_cache().last_loaded is None, "failed load must not mark the cache"

        loader.load_all_fields(None, "USA", 0, "TOP3000")
        assert fp.get_cache().last_loaded == ("USA", 0, "TOP3000")
        assert fp.get_cache().matrix_by_dataset == {"ds1": ["close"]}
        assert calls["n"] == 2
    finally:
        fp.set_cache(original)

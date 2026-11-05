"""Forum-mined template pool: signature-keyed caching and rebuild triggers."""

import json
import time

from generator import template_source as ts
from tests import test_template_source_helpers as helpers
from tests.test_template_source_helpers import FIELDS, OPS, _clear_pool  # noqa: F401

# Bound here rather than imported by name: a direct import of `corpus` would be
# shadowed by the test parameters of the same name (ruff F811).
corpus = helpers.corpus


def test_pool_is_cached_for_the_same_signature(corpus):
    first = ts.load_pool(FIELDS, OPS, corpus)
    assert ts.load_pool(FIELDS, OPS, corpus) is first


def test_pool_rebuilds_when_the_corpus_file_changes(tmp_path):
    """A re-mine is picked up at the next load, no explorer restart needed."""
    path = tmp_path / "t.json"
    path.write_text(json.dumps([{"skeleton": "rank({f})", "fillable_from_pv_option": True}]))
    assert len(ts.load_pool(FIELDS, OPS, str(path))) == 1
    time.sleep(0.01)  # distinct mtime_ns even on coarse filesystem clocks
    path.write_text(
        json.dumps(
            [
                {"skeleton": "rank({f})", "fillable_from_pv_option": True},
                {"skeleton": "ts_rank({f},5)", "fillable_from_pv_option": True},
            ]
        )
    )
    assert len(ts.load_pool(FIELDS, OPS, str(path))) == 2


def test_pool_rebuilds_when_the_field_pool_changes(corpus):
    first = ts.load_pool(FIELDS, OPS, corpus)
    second = ts.load_pool([*FIELDS, "vwap"], OPS, corpus)
    assert second is not first


def test_pool_rebuilds_when_equal_sized_pools_differ(corpus):
    """Same size, different contents: caching on size alone handed the second
    region a pool filtered against the first region's fields."""
    first = ts.load_pool(["close", "volume", "returns", "cap"], OPS, corpus)
    second = ts.load_pool(["close", "volume", "returns", "vwap"], OPS, corpus)
    assert first is not second
    # ... and the second signature is itself cached.
    assert second is ts.load_pool(["close", "volume", "returns", "vwap"], OPS, corpus)


def test_pool_rebuilds_when_equal_sized_operator_sets_differ(corpus):
    """Same operator count, different contents: keying on the count reused a
    pool filtered against the old allowlist."""
    same_size_different = (OPS - {"ts_rank"}) | {"ts_arg_max"}
    assert len(same_size_different) == len(OPS)
    first = ts.load_pool(FIELDS, OPS, corpus)
    second = ts.load_pool(FIELDS, same_size_different, corpus)
    assert first is not second
    # `ts_rank({f},20)` is no longer allowed, so only the slotless row survives.
    assert len(second) < len(first)

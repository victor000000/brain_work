"""Fixtures and constants shared by the forum template-pool test modules."""

import json

import pytest

from generator import template_source as ts

FIELDS = ["close", "volume", "returns", "cap"]
OPS = {"rank", "ts_rank", "ts_delta", "group_rank", "ts_mean", "close", "volume"}


@pytest.fixture(autouse=True)
def _clear_pool():
    ts.reset_cache()
    yield
    ts.reset_cache()


@pytest.fixture
def corpus(tmp_path):
    rows = [
        {"skeleton": "ts_rank({f},20)", "fillable_from_pv_option": True},
        {"skeleton": "rank(close)", "fillable_from_pv_option": True},
        # not pv/option fillable — must never enter the pool
        {"skeleton": "ts_rank({f},20)", "fillable_from_pv_option": False},
        # unbalanced — rejected at load by the shape parse, not at generation
        {"skeleton": "rank({f}", "fillable_from_pv_option": True},
    ]
    path = tmp_path / "t.json"
    path.write_text(json.dumps(rows))
    return str(path)

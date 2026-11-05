"""Language-specific settings survive refinement without mixed payloads."""

import json

import duckdb
import pytest

from runner.explore_helpers.polish_language import preserve_python_batch


@pytest.fixture
def db():
    with duckdb.connect(":memory:") as c:
        c.execute("CREATE TABLE alpha_results(alpha_id TEXT, raw_json TEXT)")
        yield c


CONFIG = {
    "region": "IND",
    "universe": "TOP500",
    "delay": 1,
    "language": "PYTHON",
    "lookback": 59,
    "maxTrade": "ON",
    "testPeriod": "P1Y0M",
    "decay": 4,
    "truncation": 0.08,
}
PYTHON_ROW = ("py", "source", "IND", "TOP500", 1, "STATISTICAL", 0, "")
FAST_ROW = ("fast", "rank(close)", "IND", "TOP500", 1, "STATISTICAL", 0, "")


def test_preserve_original_python_settings_and_cell(db):
    db.execute("INSERT INTO alpha_results VALUES (?,?)", ["py", json.dumps({"_submitted_settings": CONFIG})])
    cell, candidates, settings = preserve_python_batch(db, ("USA", "TOP3000", 1), [PYTHON_ROW, FAST_ROW])
    assert cell == ("IND", "TOP500", 1)
    assert candidates == [PYTHON_ROW]
    assert settings == CONFIG


def test_fast_batch_does_not_mix_python_source(db):
    db.execute("INSERT INTO alpha_results VALUES (?,?)", ["py", json.dumps({"settings": CONFIG})])
    cell, candidates, settings = preserve_python_batch(db, ("IND", "TOP500", 1), [FAST_ROW, PYTHON_ROW])
    assert cell == ("IND", "TOP500", 1)
    assert candidates == [FAST_ROW]
    assert settings is None


@pytest.mark.parametrize("patch", [{"lookback": None}, {"lookback": True}, {"region": "USA"}])
def test_invalid_python_original_never_becomes_fastexpr(db, patch):
    db.execute("INSERT INTO alpha_results VALUES (?,?)", ["py", json.dumps({"settings": {**CONFIG, **patch}})])
    with pytest.raises(ValueError):
        preserve_python_batch(db, ("IND", "TOP500", 1), [PYTHON_ROW])

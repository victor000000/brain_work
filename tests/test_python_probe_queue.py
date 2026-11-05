"""Python admission preserves source/settings and uncertain ownership."""

import json

import pytest

from core.db import connect, init_tables
from runner import probe_validation
from runner.probe_queue_store import enqueue_probe, set_probe_state
from runner.python_probe_source import python_source_identity
from runner.settings_factory import make_settings

SOURCE = """from brain.alphas import alpha
import numpy as np
@alpha(data=["returns"], store=[])
def signal(data, store):
    return np.asarray(data.returns[-1], dtype=np.float32)
"""


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(probe_validation, "target_pools", lambda *a: ({"returns"}, set(), {"industry"}))
    monkeypatch.setattr(
        probe_validation, "load_operator_names", lambda *a: pytest.fail("Python used FASTEXPR operator parser")
    )
    c = connect(":memory:")
    init_tables(c)
    yield c
    c.close()


def config():
    settings = {
        **make_settings("IND", "TOP500", 1, neutralization="STATISTICAL", decay=4, truncation=0.08),
        "language": "PYTHON",
        "lookback": 59,
    }
    settings.pop("unitHandling", None)
    settings.pop("nanHandling", None)
    return settings


def test_formatting_duplicate_preserves_uncertain_owner_and_original_source(db):
    settings = config()
    pid, inserted = enqueue_probe(db, [SOURCE], settings, ["python:pca"])
    assert inserted
    set_probe_state(db, pid, "UNCERTAIN", error="no receipt")
    formatted = "# comment\n" + SOURCE.replace('data=["returns"]', 'data = ["returns"]')
    assert enqueue_probe(db, [formatted], settings, ["python:renamed"]) == (pid, False)
    row = db.execute("SELECT state,expressions,settings FROM probe_batches WHERE probe_id=?", [pid]).fetchone()
    assert row[0] == "UNCERTAIN"
    assert json.loads(row[1]) == [SOURCE]
    assert json.loads(row[2]) == settings


def test_lookback_is_part_of_identity(db):
    settings = config()
    first = enqueue_probe(db, [SOURCE], settings, ["python:pca"])[0]
    second = enqueue_probe(db, [SOURCE], {**settings, "lookback": 60}, ["python:pca"])[0]
    assert first != second


@pytest.mark.parametrize("patch", [{"lookback": None}, {"lookback": True}, {"lookback": -1}, {"lookback": 1025}])
def test_invalid_lookback(db, patch):
    with pytest.raises(ValueError):
        enqueue_probe(db, [SOURCE], {**config(), **patch}, ["python:pca"])


def test_group_value_or_multiple_sources_rejected(db):
    with pytest.raises(ValueError):
        enqueue_probe(db, [SOURCE.replace("returns", "industry")], config(), ["python:bad"])
    with pytest.raises(ValueError):
        enqueue_probe(db, [SOURCE, SOURCE + "\n"], config(), ["python:a", "python:b"])


@pytest.mark.parametrize("setting,value", [("unitHandling", "VERIFY"), ("nanHandling", "OFF")])
def test_native_rejected_python_settings_cannot_be_queued(db, setting, value):
    with pytest.raises(ValueError, match="omit unsupported"):
        enqueue_probe(db, [SOURCE], {**config(), setting: value}, ["python:pca"])


def test_identity_keeps_string_whitespace_and_block_nesting():
    assert python_source_identity('x="a b"') != python_source_identity('x="ab"')
    assert python_source_identity("if True:\n x=1\n y=2") != python_source_identity("if True:\n x=1\ny=2")

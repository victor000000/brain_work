"""store_checks — counts, None / list / dict sanitization."""

from storage.store_checks import store_checks
from tests.test_storage.conftest import conn


def test_store_checks_counts():
    c = conn()
    checks = [
        {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0},
        {"name": "HIGH_TURNOVER", "result": "FAIL", "limit": 0.4, "value": 0.6},
        {"name": "CONCENTRATED", "result": "WARNING", "limit": 0.1, "value": 0.08},
    ]
    result = store_checks(c, "a1", checks)
    assert result == {"pass": 1, "fail": 1, "warn": 1, "pend": 0}


def test_store_checks_none_values():
    c = conn()
    checks = [{"name": "CONC_WEIGHT", "result": "FAIL", "limit": None, "value": None}]
    result = store_checks(c, "a2", checks)
    assert result["fail"] == 1


def test_store_checks_list_values():
    c = conn()
    checks = [{"name": "COMPLEX", "result": "PASS", "limit": [1, 2], "value": {"x": 1}}]
    result = store_checks(c, "a3", checks)
    assert result["pass"] == 1
    row = c.execute("SELECT limit_val, actual_val FROM submission_checks WHERE alpha_id='a3'").fetchone()
    assert row[0] is None  # list sanitized to None
    assert row[1] is None  # dict sanitized to None

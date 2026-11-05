"""Submission-check metadata survives storage without changing scalar gates."""

import json

import duckdb

from storage.store_checks import store_checks
from tests.test_storage.conftest import conn


def test_native_date_ratio_and_structured_values_are_preserved():
    checks = [
        {"name": "CONCENTRATED_WEIGHT", "result": "FAIL", "date": "2016-08-02", "limit": 0.1, "value": 0.223386},
        {
            "name": "NATIVE_DETAIL",
            "result": "PASS",
            "limit": ["RAM", "Industry"],
            "value": {"ratio": 0.4, "labels": ["行业", None]},
            "details": {"correlatedAlphas": [{"id": "example", "correlation": 0.72}]},
        },
    ]
    c = conn()
    try:
        assert store_checks(c, "metadata", checks) == {"pass": 1, "fail": 1, "warn": 0, "pend": 0}
        rows = c.execute(
            "SELECT check_name, limit_val, actual_val, extra FROM submission_checks WHERE alpha_id=?",
            ("metadata",),
        ).fetchall()
        by_name = {r[0]: r for r in rows}
        assert json.loads(by_name["CONCENTRATED_WEIGHT"][3]) == checks[0]
        assert json.loads(by_name["NATIVE_DETAIL"][3]) == checks[1]
        assert by_name["NATIVE_DETAIL"][1:3] == (None, None)
    finally:
        c.close()


def test_latest_check_payload_replaces_prior_details_without_duplication():
    original = {"name": "ROBUST", "result": "FAIL", "value": 0.6, "limit": 1.34, "ratio": 0.4}
    latest = {"name": "ROBUST", "result": "PASS", "value": 1.5, "limit": 1.34}
    c = conn()
    try:
        store_checks(c, "replace", [original])
        store_checks(c, "replace", [latest])
        rows = c.execute("SELECT result, extra FROM submission_checks WHERE alpha_id=?", ("replace",)).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "PASS"
        assert json.loads(rows[0][1]) == latest
        assert c.execute("SELECT seen_count FROM check_failures WHERE alpha_id=?", ("replace",)).fetchone()[0] == 1
        assert original["ratio"] == 0.4
    finally:
        c.close()


def test_complete_check_json_roundtrips_through_parquet(tmp_path):
    check = {"name": "LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO", "result": "FAIL", "ratio": 0.9, "limit": 2.97, "value": 2.93}
    c = conn()
    destination = tmp_path / "check_details.parquet"
    try:
        store_checks(c, "parquet", [check])
        c.execute("COPY submission_checks TO ? (FORMAT PARQUET)", (str(destination),))
        with duckdb.connect(":memory:") as reader:
            extra = reader.execute("SELECT extra FROM read_parquet(?)", (str(destination),)).fetchone()[0]
        assert json.loads(extra) == check
    finally:
        c.close()

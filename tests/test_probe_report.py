"""Probe report classification — only BRAIN rejections recommend pruning."""

import logging

from tools.probe_simulation_combos.report import report_rejects


def _result(verdict, universe="TOP3000", delay=1):
    return {"region": "USA", "universe": universe, "delay": delay, "verdict": verdict, "detail": ""}


def test_report_does_not_recommend_pruning_on_http_errors(caplog):
    with caplog.at_level(logging.INFO):
        report_rejects([_result("HTTP_500"), _result("RATE_LIMITED")])
    assert "NOT rejections" in caplog.text
    assert "prune" not in caplog.text.lower()


def test_report_recommends_pruning_only_for_brain_rejections(caplog):
    with caplog.at_level(logging.INFO):
        report_rejects([_result("REJECT_NOT_AVAILABLE"), _result("HTTP_500")])
    assert "REJECTED by BRAIN" in caplog.text
    assert "PROBE FAILED (HTTP error)" in caplog.text


def test_report_silent_when_everything_passed(caplog):
    with caplog.at_level(logging.INFO):
        report_rejects([_result("OK")])
    assert caplog.text == ""

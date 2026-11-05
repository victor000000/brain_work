"""Shared fixture and seed builder for the auto-checker selection tests.

The preview gate runs before any submit; every split module imports
`_gates_pass` so the autouse stub keeps applying to its tests, and `_seed` to
plant alpha_results rows for the selector.

Nothing stubs the correlation fetchers any more: the check path stopped
polling them on 2026-10-07 (`checker/auto_check_arms.py`), so the only
correlation input is the preview body.
"""

import pytest

from checker import auto_check


@pytest.fixture(autouse=True)
def _gates_pass(monkeypatch):
    monkeypatch.setattr(auto_check, "check_via_get", lambda session, aid: [{"name": "LOW_SHARPE", "result": "PASS"}])
    # An undecided correlation arm submits rather than deferring, because the
    # platform recomputes correlation at submit time. Stub the submit so a
    # selection test never reaches the network; a test that asserts on the
    # submission patches this again, and the later patch wins.
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: "CHECK_UNAVAILABLE")


def _seed(conn, alpha_id, sharpe, status=None, summary=False, region="USA", delay=1, categories='["pv"]'):
    conn.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, region, universe, delay, is_sharpe, is_fitness, is_turnover, test_sharpe, status, pyramid_categories) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (alpha_id, region, "TOP3000", delay, sharpe, 2.0, 0.3, 1.0, status, categories),
    )
    if summary:
        conn.execute(
            "INSERT INTO alpha_check_summary (alpha_id, pass_count, fail_count, warn_count, pend_count, checked_at) "
            "VALUES (?, 1, 0, 0, 0, 'now')",
            (alpha_id,),
        )
    conn.commit()

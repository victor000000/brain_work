"""The preview's correlation verdicts are the only source; nothing is polled.

The standalone endpoint polls were removed on 2026-10-07 — they returned
nothing for hours at a time and cost up to 120s per alpha, capping a check run
at 14 of 32 alphas. See `checker/auto_check_arms.py`."""

import pytest

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def _preview_with(prod, self_):
    return [
        {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.7},
        {"name": "PROD_CORRELATION", "result": prod[0], "limit": 0.7, "value": prod[1]},
        {"name": "SELF_CORRELATION", "result": self_[0], "limit": 0.7, "value": self_[1]},
    ]


def test_preview_correlations_are_used_instead_of_polling_the_endpoints(monkeypatch, conn):
    """The preview already carries the platform's verdict for both arms.

    Those two endpoint polls were the most expensive part of a check — 60s each
    when the endpoint is degraded — so asking again for an answer we hold was
    pure load. They are gone from the check path entirely now, which the test
    pins by driving a decision from the preview alone.
    """
    _seed(conn, "A1", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: _preview_with(("PASS", 0.31), ("PASS", 0.22)))
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "FAIL:1")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["A1"]


def test_a_preview_correlation_failure_is_recorded_without_a_submission(monkeypatch, conn):
    _seed(conn, "A1", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: _preview_with(("FAIL", 0.88), ("PASS", 0.22)))
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "SUBMITTED")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == []
    row = conn.execute(
        "SELECT result FROM submission_checks WHERE alpha_id='A1' AND check_name='PROD_CORRELATION'"
    ).fetchone()
    assert row == ("FAIL",)


def test_an_undecided_preview_arm_submits_without_polling(monkeypatch, conn):
    """`ERROR`/`PENDING` carries value=None and must never read as a pass.

    It also must not send us to the endpoint: an arm the preview left
    undecided goes straight to the submit, which is where the platform
    computes correlation anyway.
    """
    _seed(conn, "A1", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: _preview_with(("ERROR", None), ("PASS", 0.22)))
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "SUBMITTED")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["A1"]


@pytest.mark.parametrize("arm", ["prod", "self"])
def test_native_pass_above_local_correlation_limit_is_not_replaced(monkeypatch, conn, arm):
    """BRAIN explicitly passed XgRn2YRl production correlation at0.7331.

    The platform verdict can include rules absent from our local scalar limit.
    Turning its PASS into FAIL suppresses a valid submission opportunity.
    """
    _seed(conn, "NATIVE_PASS", 3.0)
    values = {"prod": ("PASS", 0.31), "self": ("PASS", 0.22)}
    values[arm] = ("PASS", 0.7331)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: _preview_with(values["prod"], values["self"]))
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "CHECK_UNAVAILABLE")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["NATIVE_PASS"]
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM submission_checks WHERE alpha_id='NATIVE_PASS' AND result='FAIL'"
        ).fetchone()[0]
        == 0
    )


def test_native_fail_below_local_correlation_limit_still_blocks(monkeypatch, conn):
    _seed(conn, "NATIVE_FAIL", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: _preview_with(("FAIL", 0.5), ("PASS", 0.22)))
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "SUBMITTED")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == []
    assert conn.execute(
        "SELECT result FROM submission_checks WHERE alpha_id='NATIVE_FAIL' AND check_name='PROD_CORRELATION'"
    ).fetchone() == ("FAIL",)

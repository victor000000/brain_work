"""The check queue is ordered by expected value, not by sharpe alone.

A run's 1200s covers only 20-36 of the 60 candidates it asks for, so the order
decides which shapes are ever looked at — and correlation, not sharpe, is what
decides a submission.
"""

from checker import auto_check
from checker.auto_check_rank import by_expected_value
from generator import corr_prior
from tests.test_runner_fixes.auto_check_helpers import _seed


def _with_template(conn, alpha_id, template, sharpe):
    _seed(conn, alpha_id, sharpe)
    conn.execute("UPDATE alpha_results SET template=? WHERE alpha_id=?", (template, alpha_id))
    conn.commit()


def test_a_penalised_shape_sorts_below_a_clean_one(monkeypatch, conn):
    # `saturated` has the better sharpe but a poor measured correlation record.
    _with_template(conn, "HIGH", "saturated", 2.4)
    _with_template(conn, "LOW", "clean", 1.9)
    monkeypatch.setattr(corr_prior, "corr_weight", lambda name, *, cell=None: 0.5 if name == "saturated" else 0.99)

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["LOW", "HIGH"], ids


def test_deferred_still_sorts_last_whatever_the_weight(monkeypatch, conn):
    """The deferral ordering is what stops an undecidable alpha heading every
    run; the re-rank must not undo it."""
    _with_template(conn, "DEFERRED", "clean", 3.0)
    _with_template(conn, "FRESH", "saturated", 1.7)
    monkeypatch.setattr(corr_prior, "corr_weight", lambda name, *, cell=None: 0.5 if name == "saturated" else 0.99)
    conn.execute("INSERT INTO check_deferrals (alpha_id, attempts, last_at) VALUES ('DEFERRED', 1, 'now')")
    conn.commit()

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["FRESH", "DEFERRED"], ids


def test_a_cold_cache_keeps_the_old_order(monkeypatch, conn):
    """With no weights loaded the factor is 1.0 everywhere, so the queue is the
    sharpe order it always was — a cold cache degrades, it does not scramble.

    Both sharpes clear the USA/d1 eligibility floor of 1.58; below it the
    selector drops them for reasons that have nothing to do with ranking."""
    _with_template(conn, "A", "one", 2.0)
    _with_template(conn, "B", "two", 1.6)
    monkeypatch.setattr(corr_prior, "corr_weight", lambda name, *, cell=None: 1.0)

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["A", "B"], ids


def test_the_window_is_wider_than_the_batch():
    """A window the size of the batch could only shuffle what sharpe chose."""
    from checker.auto_check_queue import RERANK_WINDOW

    assert RERANK_WINDOW > 1


def test_by_expected_value_truncates_to_the_limit():
    rows = [("A", 2.0, "clean", False, "USA", "TOP3000", 1), ("B", 1.0, "clean", False, "USA", "TOP3000", 1)]
    assert by_expected_value(rows, 1) == [("A", 2.0)]


def test_selector_uses_the_candidates_cell_for_correlation(monkeypatch, conn):
    _with_template(conn, "USA", "same_shape", 2.4)
    _with_template(conn, "EUR", "same_shape", 2.0)
    conn.execute("UPDATE alpha_results SET region='EUR',universe='TOP2500',delay=1 WHERE alpha_id='EUR'")
    conn.commit()
    calls = []

    def weight(name, *, cell=None):
        calls.append((name, cell))
        return 0.1 if cell == ("USA", "TOP3000", 1) else 1.0

    monkeypatch.setattr(corr_prior, "corr_weight", weight)
    assert [aid for aid, _ in auto_check._select_candidates(conn, 10)] == ["EUR", "USA"]
    assert ("same_shape", ("EUR", "TOP2500", 1)) in calls
    assert ("same_shape", ("USA", "TOP3000", 1)) in calls


def test_stored_correlation_recovery_updates_feedback_without_erasing_history(conn):
    import pytest

    from generator.corr_prior import corr_weight, load_corr_prior
    from storage.store_checks import store_checks

    _with_template(conn, "RECOVERED", "recovered_shape", 2.0)
    store_checks(conn, "RECOVERED", [{"name": "PROD_CORRELATION", "result": "FAIL", "value": 0.9, "limit": 0.7}])
    load_corr_prior(conn)
    cell = ("USA", "TOP3000", 1)
    assert corr_weight("recovered_shape", cell=cell) == pytest.approx(9 / 11)
    store_checks(conn, "RECOVERED", [{"name": "PROD_CORRELATION", "result": "PASS", "value": 0.4, "limit": 0.7}])
    load_corr_prior(conn)
    assert corr_weight("recovered_shape", cell=cell) == pytest.approx(10 / 11)
    assert conn.execute("SELECT seen_count FROM check_failures WHERE alpha_id='RECOVERED'").fetchone() == (1,)

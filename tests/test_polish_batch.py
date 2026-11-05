"""Near-miss polishing: the batch plan — cell choice and attempt budget."""

import random

from runner.explore_helpers import polish
from runner.settings_factory import ALLOWED_NEUT_BY_REGION
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _alpha, _checks, conn

__all__ = ["conn"]

# ------------------------------------------------------------------- plan ---


def test_take_batch_returns_the_expression_and_a_different_neutralization(conn):
    _alpha(conn, neut="SLOW")
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    plan = polish.take_batch(conn, random.Random(0))
    assert plan is not None
    assert plan["expressions"] == ["rank(close)"]
    assert plan["region"] == "HKG" and plan["universe"] == "TOP800" and plan["delay"] == 1
    assert plan["neutralization"] in ALLOWED_NEUT_BY_REGION["HKG"]
    assert plan["neutralization"] != "SLOW"
    assert plan["alpha_ids"] == ["A1"]


def test_take_batch_increments_attempts(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    polish.take_batch(conn, random.Random(0))
    assert conn.execute("SELECT attempts FROM polish_candidates").fetchone()[0] == 1


def test_candidates_are_retired_after_max_attempts(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    conn.execute("UPDATE polish_candidates SET attempts = ?", (polish.POLISH_MAX_ATTEMPTS,))
    assert polish.take_batch(conn, random.Random(0)) is None


def test_batch_takes_the_most_populated_cell(conn):
    """Settings are per-batch, so a batch can only carry one cell's candidates."""
    for i in range(3):
        _alpha(conn, aid=f"H{i}", region="HKG", expr=f"rank(close)+{i}")
        store_checks(conn, f"H{i}", _checks(POLISH_MIN_PASSES, 1))
    _alpha(conn, aid="U1", region="USA", expr="rank(volume)")
    store_checks(conn, "U1", _checks(POLISH_MIN_PASSES, 1))

    plan = polish.take_batch(conn, random.Random(0))
    assert plan["region"] == "HKG"
    assert len(plan["expressions"]) == polish.POLISH_MAX_EXPRS
    # Only the consumed cell's candidates were charged an attempt.
    assert conn.execute("SELECT attempts FROM polish_candidates WHERE alpha_id='U1'").fetchone()[0] == 0


# ------------------------------------------------------------------ empty ---


def test_empty_queue_returns_none(conn):
    assert polish.take_batch(conn, random.Random(0)) is None


def test_missing_table_returns_none(conn):
    conn.execute("DROP TABLE polish_candidates")
    assert polish.take_batch(conn, random.Random(0)) is None


def test_polish_re_records_provenance_from_the_source_alpha(conn):
    """A polished alpha must not come back as `unknown`.

    `polish_candidates` stores no template name, but its `alpha_id` points at
    the row that does. Without restoring it, the re-submitted expression has no
    entry in the generator's in-memory map — the original recording is days old
    or FIFO-evicted — and the alpha is stored under the name nothing weights,
    feeding neither `template_performance` nor the correlation prior.
    """
    from generator.weighted_selection import peek_expr_template
    from generator.weighted_selection.state import get_state

    saved = dict(get_state().expr_templates)
    try:
        # The fixture inserts positionally, so the column is added after it.
        _alpha(conn, neut="SLOW")
        conn.execute("ALTER TABLE alpha_results ADD COLUMN template TEXT")
        conn.execute("UPDATE alpha_results SET template = 'vwap_close_spread' WHERE alpha_id = 'A1'")
        store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
        get_state().expr_templates.clear()
        plan = polish.take_batch(conn, random.Random(0))
        assert plan is not None
        assert peek_expr_template(plan["expressions"][0]) == "vwap_close_spread"
    finally:
        get_state().expr_templates.clear()
        get_state().expr_templates.update(saved)

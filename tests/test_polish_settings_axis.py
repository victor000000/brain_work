"""Polish varies the settings on every other batch, not only the neutralization.

Measured 2026-10-11 on the 99 expressions with two or more checked alphas: 16
have one alpha that passes every check and another that fails one. On distinct
expressions, decay/truncation alone converted 9 and neutralization alone 8 — and
`take_batch` only ever varied the neutralization, so half of those conversions
were unreachable. The two axes now alternate by batch, so both stay measurable.
"""

import random

import pytest

from runner.explore_helpers import polish
from runner.setting_pools import DECAYS, TRUNCATIONS
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _checks

SCHEMA = """
CREATE TABLE alpha_results (
    alpha_id TEXT PRIMARY KEY, expression TEXT, region TEXT, universe TEXT,
    delay INTEGER, neutralization TEXT, decay INTEGER, truncation REAL
);
CREATE TABLE submission_checks (
    alpha_id TEXT, check_name TEXT, result TEXT, limit_val TEXT, actual_val TEXT, extra TEXT,
    PRIMARY KEY (alpha_id, check_name)
);
CREATE TABLE alpha_check_summary (
    alpha_id TEXT PRIMARY KEY, pass_count INTEGER, fail_count INTEGER,
    warn_count INTEGER, pend_count INTEGER, checked_at TEXT
);
CREATE TABLE check_failures (
    alpha_id TEXT, check_name TEXT, limit_val TEXT, actual_val TEXT,
    first_seen TEXT, last_seen TEXT, seen_count INTEGER,
    PRIMARY KEY (alpha_id, check_name)
);
CREATE TABLE data_fields (id TEXT, region TEXT, universe TEXT, delay INTEGER);
CREATE TABLE polish_candidates (
    alpha_id TEXT PRIMARY KEY, expression TEXT NOT NULL, region TEXT NOT NULL,
    universe TEXT NOT NULL, delay INTEGER NOT NULL, neutralization TEXT,
    attempts INTEGER NOT NULL DEFAULT 0, tried TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

# `should_polish` is `batch_idx % POLISH_EVERY == 0`; the axis is
# `(batch_idx // POLISH_EVERY) % POLISH_SETTINGS_EVERY`. With both at 2, batch 2
# is a settings batch and batch 0 a neutralization one.
SETTINGS_BATCH = polish.POLISH_EVERY
NEUT_BATCH = 0


@pytest.fixture
def conn():
    import duckdb

    c = duckdb.connect(":memory:")
    c.execute(SCHEMA)
    yield c
    c.close()


def _alpha_with_settings(conn, aid="A1", decay=5, truncation=0.08, neut="SLOW"):
    """`test_polish_helpers._alpha` inserts six columns; this schema adds the two
    the settings axis reads (decay, truncation)."""
    conn.execute(
        "INSERT INTO alpha_results VALUES (?,?,?,?,?,?,?,?)",
        (aid, "rank(close)", "HKG", "TOP800", 1, neut, decay, truncation),
    )


def _queue(conn, aid="A1"):
    store_checks(conn, aid, _checks(POLISH_MIN_PASSES, 1))


def test_the_tried_vocabulary_tags_the_two_axes():
    entry = polish.format_settings_tried(5, 0.08)
    assert entry == "SET:5:0.08"
    assert not polish.tries_neutralization(entry)
    assert polish.tries_neutralization("SECTOR"), "a bare name is a neutralization"


def test_variant_settings_avoids_the_candidates_own_pair():
    rng = random.Random(0)
    for _ in range(50):
        pair = polish.variant_settings(rng, originals={(5, 0.08)})
        assert pair != (5, 0.08)


def test_variant_settings_avoids_what_the_candidate_already_tried():
    tried = {"SET:5:0.08", "SET:8:0.1"}
    for _ in range(50):
        pair = polish.variant_settings(random.Random(1), tried=tried)
        assert polish.format_settings_tried(*pair) not in tried


def test_a_settings_batch_changes_decay_and_truncation_not_the_neutralization(conn):
    """Its whole point: isolate the axis the measurement credits."""
    _alpha_with_settings(conn, decay=5, truncation=0.08, neut="SLOW")
    _queue(conn)
    plan = polish.take_batch(conn, random.Random(0), batch_idx=SETTINGS_BATCH)
    assert plan is not None
    assert plan["neutralization"] == "SLOW", "the settings axis holds the risk model fixed"
    assert plan["decay"] is not None and plan["truncation"] is not None
    assert (plan["decay"], plan["truncation"]) != (5, 0.08)
    tried = conn.execute("SELECT tried FROM polish_candidates").fetchone()[0]
    assert tried == polish.format_settings_tried(plan["decay"], plan["truncation"])


def test_a_neutralization_batch_is_unchanged(conn):
    """The other axis keeps the old behaviour, so the two stay comparable."""
    _alpha_with_settings(conn, neut="SLOW")
    _queue(conn)
    plan = polish.take_batch(conn, random.Random(0), batch_idx=NEUT_BATCH)
    assert plan["decay"] is None and plan["truncation"] is None
    assert plan["neutralization"] != "SLOW"
    tried = conn.execute("SELECT tried FROM polish_candidates").fetchone()[0]
    assert tried == plan["neutralization"]


def test_two_settings_attempts_do_not_repeat_a_pair(conn):
    """`tried` has to cover this axis too, or the re-run is identical."""
    _alpha_with_settings(conn)
    _queue(conn)
    pairs = set()
    for seed in range(4):
        plan = polish.take_batch(conn, random.Random(seed), batch_idx=SETTINGS_BATCH)
        if plan is None:
            break
        pairs.add((plan["decay"], plan["truncation"]))
        # Re-arm the attempt budget: this test is about the pair, not the cap.
        conn.execute("UPDATE polish_candidates SET attempts = 0")
    assert len(pairs) == 4, f"a repeated pair would re-run the same simulation: {pairs}"


def test_the_pool_is_the_configured_one():
    """A pair the generator never uses would be a settings value from nowhere."""
    pair = polish.variant_settings(random.Random(3))
    assert pair[0] in DECAYS and pair[1] in TRUNCATIONS


@pytest.mark.parametrize("truncation", polish._POLISH_TRUNCATIONS)
def test_original_pair_survives_real_database_precision(conn, monkeypatch, truncation):
    # REAL is float32 in the production schema; 0.08 returns 0.07999999821186066.
    stored = conn.execute("SELECT CAST(? AS REAL)", [truncation]).fetchone()[0]
    monkeypatch.setattr(polish, "DECAYS", (5,))
    monkeypatch.setattr(polish, "_POLISH_TRUNCATIONS", (truncation,))
    assert polish.variant_settings(originals={(5, stored)}) is None


def test_precision_matching_keeps_distinct_truncations_available(monkeypatch):
    monkeypatch.setattr(polish, "DECAYS", (5,))
    monkeypatch.setattr(polish, "_POLISH_TRUNCATIONS", (0.08,))
    assert polish.variant_settings(originals={(5, 0.0801)}) == (5, 0.08)

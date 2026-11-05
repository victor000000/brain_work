"""pyramid3_weighted_pick multiplies pyramid_score by cell_yield_posterior."""

from unittest.mock import patch

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    # Categories must be in scope (pv/option) and satisfiable, or pyramid3
    # filters the target out before the yield-weighted draw.
    c.execute("""
        CREATE TABLE data_fields (
            id TEXT, dataset_id TEXT, category_id TEXT,
            region TEXT, delay INTEGER, universe TEXT,
            type TEXT, coverage REAL, date_coverage REAL
        )
    """)
    c.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?, 'MATRIX', 0.9, 0.9)",
        [
            ("close", "pv1", "pv", "CHN", 0, "TOP2000U"),
            ("opt_iv", "option8", "option", "EUR", 0, "TOP400"),
        ],
    )
    from tools.refresh_pyramid_targets.quarter import quarter_bounds

    # Two pyramid targets, same score, different yield posterior
    c.execute(
        "INSERT INTO pyramid_targets (region, delay, category, alpha_count, multiplier, gap_to_3, score, refreshed_at) "
        "VALUES ('CHN', 0, 'pv', 0, 1.9, 3, 1.9, 0)"
    )
    c.execute(
        "INSERT INTO pyramid_targets (region, delay, category, alpha_count, multiplier, gap_to_3, score, refreshed_at) "
        "VALUES ('EUR', 0, 'option', 0, 1.9, 3, 1.9, 0)"
    )
    c.execute(
        "INSERT INTO cell_yield_posterior (region, universe, delay, count, eligible, posterior, refreshed_at) "
        "VALUES ('CHN', 'TOP2000U', 0, 1000, 27, 0.0265, 0)"
    )
    c.execute(
        "INSERT INTO cell_yield_posterior (region, universe, delay, count, eligible, posterior, refreshed_at) "
        "VALUES ('EUR', 'TOP400', 0, 10000, 0, 0.0001, 0)"
    )
    c.execute("UPDATE pyramid_targets SET period_start=?, period_end=?", quarter_bounds())
    c.commit()
    yield c
    c.close()


def test_high_posterior_cell_wins_at_equal_pyramid_score(conn):
    from generator.diversity_picker import pyramid3, yield_cache

    yield_cache.load_cell_yield_posterior(conn)
    configs = [("CHN", "TOP2000U", 0), ("EUR", "TOP400", 0)]
    with (
        patch("generator.diversity_picker.pyramid3.random.random", return_value=0.001),
        patch(
            "generator.diversity_picker.pyramid3.random.choice",
            side_effect=lambda x: x[0],
        ),
    ):
        cfg, _cat = pyramid3.pyramid3_weighted_pick(conn, configs)
    assert cfg is not None and cfg[0] == "CHN"


def test_a_filled_pyramid_is_still_reachable(conn):
    """`score = gap_to_3 * multiplier` is 0 for a pyramid we have filled, and
    the eligibility filter used to read that as "this cell is finished".

    Measured 2026-10-10: HKG/d1/pv filled — 16 submitted alphas against a
    target of 3 — so the row scored 0.0 and HKG stopped being generated for 15
    hours, taking the day's yield from 5.00% to 0.13%. HKG produced 328 of the
    359 alphas above the floor in four days; every other region combined, 31.
    """
    from generator.diversity_picker import pyramid3, yield_cache

    # CHN keeps the strong posterior (0.0265) but its pyramid is now full.
    conn.execute("UPDATE pyramid_targets SET score=0.0, gap_to_3=0, alpha_count=16 WHERE region='CHN'")
    conn.commit()
    yield_cache.load_cell_yield_posterior(conn)
    configs = [("CHN", "TOP2000U", 0), ("EUR", "TOP400", 0)]

    eligible = pyramid3._eligible_rows(conn, configs)
    assert any(row[0] == "CHN" for row, _cfgs in eligible), "the filled cell left the candidate set"

    # Statistical, not a seeded single draw: `_weighted_choice` walks `eligible`
    # in SQL order, which is not guaranteed, so one low `random()` returns
    # whichever row happens to come first. CHN holds 0.053 of the 0.058 total.
    picks = [pyramid3.pyramid3_weighted_pick(conn, configs)[0][0] for _ in range(300)]
    assert picks.count("CHN") > 240, f"the filled cell is unreachable: {picks.count('CHN')}/300"


def test_a_dominant_cell_cannot_take_everything(conn):
    """The exploration floor: every eligible row keeps a share of the top one.

    Measured 2026-10-07 — HKG/d1/pv took 60.1% of batches across 12 rows and
    then saturated on SELF_CORRELATION, so the cell that produced every
    acceptance became the one that could not be submitted.
    """
    from generator.diversity_picker import pyramid3, yield_cache
    from generator.diversity_picker.pyramid3 import EXPLORE_FLOOR

    yield_cache.load_cell_yield_posterior(conn)
    eligible = [
        (("CHN", 0, "pv", 1.9), [("CHN", "TOP2000U", 0)]),
        (("EUR", 0, "option", 1.9), [("EUR", "TOP400", 0)]),
    ]
    # Raw weights are 0.0504 and 0.00019 — a 265x spread. The floor compresses
    # it to EXPLORE_FLOOR, so the weak row keeps that fraction of the strong one.
    top = 1.9 * 0.0265
    floored = max(1.9 * 0.0001, EXPLORE_FLOOR * top)
    share = floored / (floored + top)
    assert share >= EXPLORE_FLOOR / (1 + EXPLORE_FLOOR) - 1e-9

    # And the draw can now actually reach the weak row: an unfloored weight
    # would need random() < 0.0037 of the total.
    with patch("generator.diversity_picker.pyramid3.random.random", return_value=0.9999):
        row, _cfgs = pyramid3._weighted_choice(eligible)
    assert row[0] == "EUR", "the weak cell is still unreachable"

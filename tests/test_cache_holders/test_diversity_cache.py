"""F6 cache-holder tests for DiversityCache + module-attr publishing."""

import generator.diversity_weights as dw
from core.db import connect


def test_diversity_cache_reset():
    s = dw.DiversityCache()
    s.region_config_weights = {("USA", "TOP3000", 1): 0.5}
    s.neutralization_weights = {"MARKET": 0.1}
    s.reset()
    assert s.region_config_weights == {}
    assert s.neutralization_weights == {}


def test_diversity_module_attrs_track_state():
    """Legacy direct-attribute reads (`dw._neutralization_weights`) must reflect
    whatever state is currently active."""
    fresh = dw.DiversityCache()
    fresh.neutralization_weights = {"MARKET": 0.5}
    dw.set_state(fresh)
    try:
        assert dw._neutralization_weights == {"MARKET": 0.5}
    finally:
        dw.set_state(dw.DiversityCache())


def test_diversity_load_populates_weights():
    """End-to-end: load_diversity_weights against an in-memory DB should
    populate every weight map and re-publish the module attributes."""
    conn = connect(":memory:")
    conn.execute("""
        CREATE TABLE alpha_results (
            neutralization TEXT, decay INT, truncation REAL,
            region TEXT, universe TEXT, delay INT,
            is_sharpe REAL, raw_json TEXT, pyramid_categories TEXT
        )
    """)
    # pyramid_categories must be present and pv/option — weights are fitted only
    # on alphas the generator can still reach.
    conn.executemany(
        "INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("MARKET", 4, 0.08, "USA", "TOP3000", 1, 1.5, '{"settings":{"testPeriod":"P1Y0M"}}', '["pv"]'),
            ("SECTOR", 4, 0.08, "USA", "TOP3000", 1, 0.2, None, '["pv"]'),
        ],
    )

    fresh = dw.DiversityCache()
    dw.set_state(fresh)
    try:
        dw.load_diversity_weights(conn)
        assert "MARKET" in fresh.neutralization_weights
        assert "SECTOR" in fresh.neutralization_weights
        assert dw._neutralization_weights is fresh.neutralization_weights
    finally:
        dw.set_state(dw.DiversityCache())

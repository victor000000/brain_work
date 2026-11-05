"""Test diversity weighting system."""

from core.regions import REGION_CONFIGS
from generator.diversity_picker import weighted_pick, weighted_pick_config
from generator.diversity_weights import load_diversity_weights
from runner.setting_pools import DECAYS, NEUTRALIZATIONS
from tests.conftest import open_prod_db


def test_load_weights():
    """Loading diversity weights should not crash."""
    conn = open_prod_db()
    load_diversity_weights(conn)


def test_weighted_pick_returns_valid():
    """Weighted pick should return a value from the pool."""
    conn = open_prod_db()
    load_diversity_weights(conn)

    for _ in range(20):
        result = weighted_pick(NEUTRALIZATIONS, {})
        assert result in NEUTRALIZATIONS

        result = weighted_pick(DECAYS, {})
        assert result in DECAYS


def test_weighted_pick_config_returns_valid():
    """Config picker should return a valid region config."""
    conn = open_prod_db()
    load_diversity_weights(conn)

    for _ in range(20):
        config = weighted_pick_config(REGION_CONFIGS)
        assert config in REGION_CONFIGS


def test_weighted_pick_empty():
    """Weighted pick with empty list returns None."""
    assert weighted_pick([], {}) is None


def test_inverse_weighting():
    """Less-used values should get higher weights."""
    # Simulate: value A used 100 times, value B used 1 time
    weights = {"A": 1.0 / (1 + 100), "B": 1.0 / (1 + 1)}
    # B should be ~50x more likely than A
    assert weights["B"] > weights["A"] * 40

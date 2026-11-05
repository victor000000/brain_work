"""Tier weights must be compressed so a single near-complete pyramid
cannot dominate selection by 1000x."""

from tools.refresh_pyramid_targets.score import GAP_TIER_WEIGHT, compute_targets


def test_tier_weights_compressed():
    """Gap=1 must be no more than 10x gap=3 (was 1000x)."""
    assert GAP_TIER_WEIGHT[0] == 0.0
    assert GAP_TIER_WEIGHT[1] == 10.0
    assert GAP_TIER_WEIGHT[2] == 3.0
    assert GAP_TIER_WEIGHT[3] == 1.0


def test_compute_targets_score_uses_new_tiers():
    """A gap=1 cell with mult=1.7 should score 17.0, not 1700.0."""
    alphas = [{"category": {"id": "model"}, "region": "EUR", "delay": 0, "alphaCount": 2}]
    mults = [{"category": {"id": "model"}, "region": "EUR", "delay": 0, "multiplier": 1.7}]
    rows = compute_targets(alphas, mults, "2026-04-01", "2026-06-30", 1700000000)
    assert len(rows) == 1
    assert rows[0]["gap_to_3"] == 1
    assert rows[0]["score"] == 17.0

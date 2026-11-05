"""`_alpha_max_multiplier`: the destination-cell multiplier for one alpha.

Split out of `tests/test_f3_pyramid.py`.
"""


def test_alpha_max_multiplier_picks_max_across_cats():
    """Multi-category alpha earns max(multiplier) across its categories."""
    from generator.priors_loader import _alpha_max_multiplier

    mults = {("pv", "USA", 1): 1.4, ("risk", "USA", 1): 1.7}
    counts = {}  # below saturation cap
    assert _alpha_max_multiplier(["pv", "risk"], "USA", 1, mults, counts) == 1.7


def test_alpha_max_multiplier_caps_saturated_cells():
    """A destination pyramid cell with >3 alphas clips multiplier to 1.0."""
    from generator.priors_loader import _alpha_max_multiplier

    mults = {("pv", "USA", 1): 1.9}
    counts = {("pv", "USA", 1): 4}  # > _SATURATION_CAP_N
    assert _alpha_max_multiplier(["pv"], "USA", 1, mults, counts) == 1.0


def test_alpha_max_multiplier_no_resolvable_cats_returns_none():
    """No category resolves → None (caller falls back to 1.0 for the cell)."""
    from generator.priors_loader import _alpha_max_multiplier

    assert _alpha_max_multiplier(["unknown"], "USA", 1, {}, {}) is None

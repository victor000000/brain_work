"""F3 cell-priors cache.

Pure read API for the explorer. Populated by `priors_loader.refresh_priors`,
consumed by `weighted_selection.weighted_choice` to bias template selection
toward cells with proven hit rates, high pyramid multipliers, and high
out-of-sample robustness.

Cell key for selection: (template, region, universe, delay) — the full
(template, region, universe, delay, neutralization) cell is recorded in
`submission_outcomes`, but for selection we marginalize over neutralization.
"""

from core.log import get_file_logger

# Beta(alpha=1, beta=49) prior on hit rate (P(is_sharpe >= 1.0)).
_PRIOR_MEAN = 1.0 / (1.0 + 49.0)

# Default expected_multiplier for unknown cells = 1.0 (no pyramid bias).
_DEFAULT_EXPECTED_MULTIPLIER = 1.0

# Default OOS robustness = 0.5 (Beta(1,1) prior mean).
_DEFAULT_OOS_ROBUSTNESS = 0.5

# Cache value shape: (hit_weight, quarantined, expected_multiplier, oos_robustness).
_priors: dict[tuple[str, str, str, int], tuple[float, bool, float, float]] = {}

plog = get_file_logger("generator")


def load_priors(conn) -> None:
    """Replace the in-memory cache with the current cell_priors table contents."""
    global _priors
    rows = conn.execute(
        "SELECT template, region, universe, delay, hit_weight, quarantined, "
        "expected_multiplier, oos_robustness FROM cell_priors"
    ).fetchall()
    _priors = {(t, r, u, d): (float(hw), bool(q), float(em), float(oos)) for t, r, u, d, hw, q, em, oos in rows}
    plog.debug("loaded %d cell priors", len(_priors))


def hit_weight(template: str, region: str, universe: str, delay: int) -> float:
    """Return hit_weight for the marginal cell, with three branches:

    - quarantined cell -> 0.0 (selection-suppressed; ε-floor in weighted_choice
      keeps a small exploration probability)
    - known non-quarantined cell -> stored hit_weight
    - unknown cell -> prior mean (0.02)
    """
    cached = _priors.get((template, region, universe, delay))
    if cached is None:
        return _PRIOR_MEAN
    hw, quarantined, _em, _oos = cached
    if quarantined:
        return 0.0
    return hw


def expected_multiplier(template: str, region: str, universe: str, delay: int) -> float:
    """Return expected_multiplier for the marginal cell."""
    cached = _priors.get((template, region, universe, delay))
    if cached is None:
        return _DEFAULT_EXPECTED_MULTIPLIER
    _hw, _q, em, _oos = cached
    return em


def oos_robustness(template: str, region: str, universe: str, delay: int) -> float:
    """Return oos_robustness for the marginal cell.

    - known cell -> stored oos_robustness
    - unknown cell -> default 0.5 (prior mean, neutral)
    """
    cached = _priors.get((template, region, universe, delay))
    if cached is None:
        return _DEFAULT_OOS_ROBUSTNESS
    _hw, _q, _em, oos = cached
    return oos

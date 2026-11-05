"""In-memory cache of cell_yield_posterior, mirrors generator/cell_priors.py shape.

Loaded by runner/explore_helpers/maintenance.py on the same 50-alpha cadence
as cell_priors. Read by generator/diversity_picker/pyramid3.py to blend the
empirical yield posterior into pyramid score-based selection.
"""

from core.log import get_file_logger
from generator.priors_loader._constants import _YIELD_ALPHA, _YIELD_BETA

_PRIOR_MEAN = _YIELD_ALPHA / (_YIELD_ALPHA + _YIELD_BETA)

_yield_posterior: dict[tuple[str, str, int], float] = {}

plog = get_file_logger("diversity")


def load_cell_yield_posterior(conn) -> None:
    """Replace cache with the current cell_yield_posterior contents."""
    global _yield_posterior
    rows = conn.execute("SELECT region, universe, delay, posterior FROM cell_yield_posterior").fetchall()
    _yield_posterior = {(r, u, d): float(p) for r, u, d, p in rows}
    plog.debug("loaded %d cell_yield_posterior rows", len(_yield_posterior))


def posterior(region: str, universe: str, delay: int) -> float:
    """Return Beta-Bernoulli yield posterior for the cell, or prior mean if unknown."""
    return _yield_posterior.get((region, universe, delay), _PRIOR_MEAN)

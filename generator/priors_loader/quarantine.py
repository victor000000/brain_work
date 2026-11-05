"""Tier-2 quarantine decision logic for cell priors.

Per marginal cell (sum over neutralization):
  - sum(rejected) >= K (5) AND sum(submitted) == 0 → candidate for quarantine.
Lift criteria (any one):
  - hit_weight rebounded above 0.04 → recovery wins.
  - now - quarantined_at >= 24h → time-based lift (may re-quarantine).
"""

from generator.priors_loader._constants import (
    _QUARANTINE_DURATION_SECONDS,
    _QUARANTINE_K,
    _RECOVERY_HIT_WEIGHT,
)


def decide(rejected, submitted, hit_weight, prior_qa, now):
    """Return (quarantined_flag, quarantined_at_or_none) for a cell."""
    should_quarantine = rejected >= _QUARANTINE_K and submitted == 0
    hit_weight_recovered = hit_weight > _RECOVERY_HIT_WEIGHT
    time_lift = prior_qa is not None and (now - prior_qa) >= _QUARANTINE_DURATION_SECONDS

    if hit_weight_recovered:
        # Recovery wins over everything; do not quarantine.
        return 0, None
    if should_quarantine and not time_lift:
        # Fresh quarantine, or maintain existing (preserve original timestamp).
        return 1, (now if prior_qa is None else prior_qa)
    if should_quarantine and time_lift:
        # Time lift fires, but cell still meets criteria → re-quarantine
        # with a fresh timestamp so the next M window starts now.
        return 1, now
    return 0, None

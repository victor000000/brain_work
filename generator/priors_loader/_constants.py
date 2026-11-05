"""Tunable thresholds for the priors recompute / quarantine logic."""

# Beta-Bernoulli prior on hit-rate. Mean = ALPHA / (ALPHA + BETA) = 0.02.
_ALPHA = 1.0
_BETA = 49.0

# Tier-2 quarantine: cell with K rejections and 0 submissions is suppressed.
_QUARANTINE_K = 5

# Auto-lift window: 24h. After that, the cell is reconsidered.
_QUARANTINE_DURATION_SECONDS = 86400

# Recovery override: if hit_weight rebounds above 2x the prior mean, the
# cell un-quarantines unconditionally (the empirical signal trumps the rule).
_RECOVERY_HIT_WEIGHT = 0.04

# Pyramid saturation cap: a destination pyramid cell with > N alphas already
# clips its multiplier to 1.0 (no extra incentive once the cell is full).
_SATURATION_CAP_N = 3

# OOS-robustness Beta-Bernoulli prior. Weaker than hit-rate prior because
# test_sharpe converges faster: posterior responds to ~10s of observations.
_OOS_ALPHA = 1.0
_OOS_BETA = 1.0

# Robustness threshold: test_sharpe must be at least this fraction of
# is_sharpe for an alpha to count as "robust."
_OOS_RATIO_THRESHOLD = 0.5

# Yield posterior Beta-Bernoulli prior. The baseline must match the success
# event's own base rate, and that event changed on 2026-10-12 from "passed local
# eligibility" to "cleared its checks" (see `yield_posterior.fetch_yield_counts`
# for why). Measured across the full table: 15 clears in 214,359 generated
# alphas, a base rate of 7.0e-5, so the 1/50 = 0.02 baseline that matched the
# gate is now 286x too high.
#
# Leaving it would not merely mis-scale the known cells — it would invert the
# allocation. `_weighted_choice` and `yield_cache.posterior` both substitute
# this mean for any cell with no row, so a prior 30x above every measured value
# hands the budget to cells the allocator has never measured. Beta is large
# because the event is rare: at 49 a 500-alpha cell with no clears would read
# 25x the population rate by default instead of shrinking toward it.
_YIELD_ALPHA = 1.0
_YIELD_BETA = 14000.0

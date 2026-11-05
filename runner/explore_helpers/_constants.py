"""Shared constants for explore-loop helpers."""

from core.log import get_file_logger

# Number of expressions per submitted batch.
BATCH_SIZE = 10

# Periodic maintenance fires every CHECK_INTERVAL completed batches
# (done_count counts batches, not alphas; each batch is BATCH_SIZE alphas).
CHECK_INTERVAL = 50

# The submission check fires on its own, shorter cadence. It shares the counter
# above only because it used to be one call: at ~46 batches per half hour,
# CHECK_INTERVAL meant a gate-passing alpha waited ~30 minutes before anything
# looked at it, and every restart reset the counter and pushed it out again.
# The check itself is a preview GET per new alpha (only alphas with no FAIL cost
# a submission attempt), so it is cheap; the heavy refreshes on CHECK_INTERVAL —
# priors, pyramid, cell-yield rebuilds — are the expensive part and stay put.
CHECK_INTERVAL_SUBMIT = 10

# ...and at least this often when no batches are completing. The batch counters
# above stop moving once the simulation budget is exhausted (the loop sleeps
# until the reset, and `done_count` only rises when a batch completes), so a
# check keyed only on completions stops for the whole idle window — on
# 2026-10-05 that left 62 eligible alphas unexamined for the 14 hours until the
# reset, when checks cost no simulation budget and any that passes every check
# is submitted on the spot.
CHECK_MAX_IDLE_SEC = 1800

elog = get_file_logger("explore")

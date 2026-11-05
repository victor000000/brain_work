"""Constants + shared logger for the explorer loop modules."""

from core.log import get_file_logger

# Slow-job reporting thresholds only; elapsed time never authorizes cancellation.
STALE_TIMEOUT = 1200  # 20 minutes

# ...but age alone is a poor staleness test: HKG/TOP800 batches routinely sit
# around 35% at the 20-minute mark and then finish. Dropping one discards
# simulations the budget has already paid for, so a batch is only stale once
# it has actually stopped advancing for this long.
STALL_GRACE_SEC = 300  # 5 minutes without progress

# Report even advancing jobs past this age; keep their accepted handles.
STALE_HARD_TIMEOUT = 3600  # 60 minutes

elog = get_file_logger("explore")

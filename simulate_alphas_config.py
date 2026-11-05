"""Tunables for the explorer entry point.

Split out of `simulate_alphas.py`, which re-exports these so `main` still reads
them from its own module globals — the tests patch `simulate_alphas.MAX_RESTARTS`
and friends there, so they must stay attributes of that module.
"""

import os

# Eight is the documented multi-simulation parent limit. A six-slot default
# was introduced after account-wide refusals on 2026-10-08; that observation
# does not establish a permanent per-runner entitlement. Re-test eight after
# recovery fixes, with native CONCURRENT handling retaining account-wide
# backoff when other sessions occupy slots. BRAIN_MAX_CONCURRENT remains an
# explicit operational override. Accepted parents are always reattached.
MAX_CONCURRENT = int(os.environ.get("BRAIN_MAX_CONCURRENT", "8"))

MAX_RESTARTS = 10
RESTART_DELAY = 30

# After this much healthy run time, prior crash history is considered stale and
# the restart counter resets — a process that crashes once an hour forever must
# not die after 10 lifetime crashes.
HEALTHY_RUN_SEC = 900

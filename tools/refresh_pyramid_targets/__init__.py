"""Refresh pyramid_targets table — package layout.

Pulls live (alpha_count, multiplier) per pyramid from BRAIN, computes the
tiered completion-priority score, and stores it. Refreshes append to
`pyramid_targets_history` (append-only, one row per period/refresh) and update
the current `pyramid_targets` snapshot; no existing period's rows are removed.

CLI: `python3 -m tools.refresh_pyramid_targets [--period current|all] [--apply]`

The default is a dry run; `--apply` is required before anything is written.
"""

from tools.refresh_pyramid_targets.runner import main
from tools.refresh_pyramid_targets.score import GAP_TIER_WEIGHT, compute_targets

__all__ = ["GAP_TIER_WEIGHT", "compute_targets", "main"]

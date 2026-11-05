"""Explorer loop — package layout.

Public API:
  run_explore_loop(session, conn, max_concurrent) — main entry point.
  STALE_TIMEOUT — seconds before an in-flight batch is considered stale.
"""

from runner.explore_loop.constants import STALE_TIMEOUT
from runner.explore_loop.loop import run_explore_loop

__all__ = ["STALE_TIMEOUT", "run_explore_loop"]

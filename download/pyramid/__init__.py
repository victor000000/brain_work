"""Pyramid multipliers + alpha-count fetcher and snapshot store — package layout.

Phase 1 of pyramid awareness — read-only fetch + persist; no submission policy.
See docs/superpowers/specs/2026-04-26-pyramid-awareness-design.md.

Public API kept stable for callers that use `from download.pyramid import ...`.
"""

# `time` is re-exported because tests reference `download.pyramid.time`
# directly (monkeypatching `time.time` to drive the staleness logic).
import time  # noqa: F401

from download.pyramid.fetch import API_BASE, fetch_pyramid_state
from download.pyramid.queries import get_current_pyramid_state
from download.pyramid.refresh import refresh_if_stale
from download.pyramid.store import store_pyramid_state

__all__ = [
    "API_BASE",
    "fetch_pyramid_state",
    "get_current_pyramid_state",
    "refresh_if_stale",
    "store_pyramid_state",
]

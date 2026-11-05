"""The swallow-and-continue refresh helpers of `periodic_maintenance`.

Split out of `runner/explore_helpers/maintenance.py`, which re-exports them —
`periodic_maintenance` calls these through its own module globals so tests can
stub them. None of them may raise: a DB-write or auth failure must not crash
the explorer's main loop, and each logs and continues instead.
"""

from download.pyramid import refresh_if_stale
from download.pyramid.quarter_targets import refresh_quarter_targets
from generator.corr_prior import load_corr_prior
from generator.priors_loader import refresh_priors
from generator.priors_loader.yield_posterior import refresh_cell_yield_posterior
from runner.explore_helpers._constants import elog


def _refresh_pyramid_state(session, conn):
    """6h staleness gate; swallow exceptions so a DB-write or auth failure
    cannot crash the explorer's main loop. refresh_if_stale already absorbs
    HTTP/JSON failures internally; this guard is for the store_pyramid_state
    propagation path documented in its docstring."""
    try:
        refresh_if_stale(session, conn, max_age_seconds=21600)
    except Exception as exc:
        elog.warning("refresh_if_stale raised, continuing: %s", exc)
    try:
        refresh_quarter_targets(session, conn, max_age_seconds=21600)
    except Exception as exc:
        elog.warning("refresh_quarter_targets raised, continuing: %s", exc)


def _refresh_cell_priors(conn):
    """F3 cell-priors refresh — same swallow-and-continue contract."""
    try:
        refresh_priors(conn)
    except Exception as exc:
        elog.warning("refresh_priors raised, continuing: %s", exc)


def _refresh_corr_prior(conn):
    """Per-template correlation weights — same swallow-and-continue contract.

    Loaded on the same cadence as the cell priors: both are read from the same
    check/submission record, so refreshing them apart would let the allocator
    mix a stale correlation rate with a fresh hit rate.
    """
    try:
        load_corr_prior(conn)
    except Exception as exc:
        elog.warning("load_corr_prior raised, continuing: %s", exc)


def _refresh_cell_yield_posterior(conn):
    """Refresh per-(region, universe, delay) yield posterior; swallow exceptions."""
    try:
        refresh_cell_yield_posterior(conn)
    except Exception as exc:
        elog.warning("refresh_cell_yield_posterior raised, continuing: %s", exc)

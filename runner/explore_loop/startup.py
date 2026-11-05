"""What a restart must restore before the loop generates anything.

Split out of `runner/explore_loop/loop.py`, which re-exports `_startup_checks`
— the tests patch the loaders through that module's globals.
"""

from core.db.health import require_usable_connection
from download.pyramid.quarter_targets import refresh_quarter_targets
from generator import cell_priors
from generator.corr_prior import load_corr_prior
from generator.diversity_picker.yield_cache import load_cell_yield_posterior
from generator.diversity_weights import load_diversity_weights
from generator.priors_loader.yield_posterior import refresh_cell_yield_posterior
from runner.explore_helpers.background_check import start_background_check
from runner.explore_loop.constants import elog


def _startup_checks(session, conn) -> None:
    """Load the learned caches, then kick one submission check.

    The interval-based check trigger counts completed batches from process
    start, so with restarts every few minutes the check queue was starved — no
    alpha was previewed for hours while thousands accumulated. Firing once at
    startup makes a restart *drain* the queue instead of postponing it;
    `start_background_check` is non-blocking and no-ops on an empty queue.

    The *learned* caches are loaded here too, and loading is the point rather
    than recomputing: `cell_priors` and `corr_prior` are module-level caches
    with no default state, so between a restart and the first
    `periodic_maintenance` — 50 completed alphas — every template scored the
    same and both the F3 feedback loop and the correlation weight were
    silently off. Measured 2026-10-07: the weights loaded at 07:17, the
    explorer restarted at 07:41, and generation ran blind until the next
    maintenance. `refresh_priors` still recomputes on its own cadence; this
    only restores what the last recompute already wrote.
    """
    # One guard per loader, not one around the block: a failure in the first
    # used to skip every loader after it, so a single DB hiccup at startup left
    # some caches populated and others empty with nothing to say which. Same
    # swallow-and-continue contract as `maintenance_refresh`.
    for label, loader in (
        ("quarterly pyramid targets", lambda c: refresh_quarter_targets(session, c)),
        ("diversity weights", lambda c: load_diversity_weights(c, force=True)),
        ("cell yield posterior", refresh_cell_yield_posterior),
        ("cell yield cache", load_cell_yield_posterior),
        ("cell priors", cell_priors.load_priors),
        ("correlation weights", load_corr_prior),
    ):
        try:
            loader(conn)
        except Exception as e:
            if conn is not None:
                require_usable_connection(conn)
            elog.warning("Startup %s load failed (continuing): %s", label, e)
    try:
        start_background_check()
    except Exception as e:
        elog.error("Startup submission check failed (continuing): %s", e, exc_info=True)

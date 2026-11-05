"""Periodic maintenance: reload weights, refresh pyramid + cell priors, run checks.

The refresh helpers live in `maintenance_refresh` and are re-exported here:
`periodic_maintenance` resolves each one through this module's globals, which
is what lets tests stub them.
"""

import time

from generator.diversity_picker.yield_cache import load_cell_yield_posterior
from generator.diversity_weights import load_diversity_weights
from runner.explore_helpers._constants import CHECK_INTERVAL, CHECK_INTERVAL_SUBMIT, CHECK_MAX_IDLE_SEC, elog
from runner.explore_helpers.background_check import start_background_check
from runner.explore_helpers.maintenance_refresh import (
    _refresh_cell_priors,
    _refresh_cell_yield_posterior,
    _refresh_corr_prior,
    _refresh_pyramid_state,
)
from runner.submit.flow import drain_held_queue


def _drain_held(session, conn):
    """Submit held (cooldown-queued) alphas whose cell has left cooldown.

    Bounded per pass; swallow errors so the maintenance path cannot crash the
    explorer if a submit probe fails.
    """
    try:
        drained = drain_held_queue(session, conn)
        if drained:
            elog.info("Drained %d held alpha(s)", drained)
    except Exception as exc:
        elog.warning("drain_held_queue raised, continuing: %s", exc)


def _log_progress(state, conn):
    total = conn.execute("SELECT COUNT(*) FROM alpha_results").fetchone()[0]
    inflight_info = ", ".join(
        f"B{b['idx']}({b['settings']['region']}/{b['settings']['universe']})" for b in state["inflight"]
    )
    elog.info(
        "Progress: %d done, %d in-flight [%s], %d total",
        state["done_count"],
        len(state["inflight"]),
        inflight_info,
        total,
    )


def periodic_maintenance(state, conn, session, freed):
    """Reload weights and check submissions periodically.

    Gating on `done >= last_check_done + CHECK_INTERVAL` (rather than
    `done % CHECK_INTERVAL == 0`) ensures the heavy maintenance fires exactly
    once per CHECK_INTERVAL completions. The modulo form re-fired every
    iteration the loop sat at a multiple-of-50 boundary, repeatedly running
    refresh_priors / refresh_pyramid / load_diversity_weights / progress query.
    """
    done = state["done_count"]
    last = state.get("last_check_done", 0)
    _drain_held(session, conn)

    # Submission check first, on its own shorter cadence: it is the path that
    # turns a gate-passing alpha into a submission, and it must not wait on the
    # heavy refreshes below. `start_background_check` no-ops while its thread is
    # still running, so a short interval cannot stack up work.
    last_submit = state.get("last_submit_check_done", 0)
    last_submit_ts = state.get("last_submit_check_ts", 0.0)
    by_progress = done > 0 and done >= last_submit + CHECK_INTERVAL_SUBMIT
    by_clock = (time.time() - last_submit_ts) >= CHECK_MAX_IDLE_SEC
    if by_progress or by_clock:
        start_background_check()
        state["last_submit_check_done"] = done
        state["last_submit_check_ts"] = time.time()

    if done > 0 and done >= last + CHECK_INTERVAL:
        load_diversity_weights(conn, force=True)
        _refresh_pyramid_state(session, conn)
        _refresh_cell_priors(conn)
        _refresh_corr_prior(conn)
        _refresh_cell_yield_posterior(conn)
        load_cell_yield_posterior(conn)
        _log_progress(state, conn)
        state["last_check_done"] = done
    elif done > 0 and freed and done % 10 == 0:
        load_diversity_weights(conn, force=True)
        elog.debug("Diversity weights reloaded (done=%d, freed=%d)", done, freed)

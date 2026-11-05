#!/usr/bin/env python3
"""Explorer entry point — starts the explore loop."""

import inspect
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

from core.auth import get_session
from core.db import get_conn, init_tables
from core.db.health import UnusableConnectionError
from core.log import get_file_logger, setup_logging
from runner.explore_loop import run_explore_loop
from simulate_alphas_config import (
    HEALTHY_RUN_SEC,
    MAX_CONCURRENT,
    MAX_RESTARTS,
    RESTART_DELAY,
)

log = setup_logging()
elog = get_file_logger("explore")


def _new_session():
    """Create an authenticated session.

    Uses core.auth.get_session(raise_on_failure=True) when that parameter
    exists (it raises instead of sys.exit); falls back to the legacy signature.
    """
    try:
        params = inspect.signature(get_session).parameters
    except (TypeError, ValueError):
        params = {}
    if "raise_on_failure" in params:
        return get_session(raise_on_failure=True)
    return get_session()


def _session_or_none():
    """Authenticate, converting both exceptions and SystemExit into None."""
    try:
        return _new_session()
    except (Exception, SystemExit) as e:
        elog.error("Authentication failed: %s", e)
        log.error("Authentication failed: %s", e)
        return None


def main():
    conn = get_conn()
    # Persist indexes restored from WAL before DDL or automatic checkpoints.
    # DuckDB 1.5.6 reproduces upstream #26106 without this explicit checkpoint.
    conn.execute("CHECKPOINT")
    init_tables(conn)
    session = _session_or_none()
    if session is None:
        elog.error("Explorer cannot start without a session, exiting")
        return 1

    elog.info("Explorer starting: max_concurrent=%d", MAX_CONCURRENT)
    log.info("Explorer starting: max_concurrent=%d", MAX_CONCURRENT)

    restarts = 0
    window_start = time.time()
    while restarts < MAX_RESTARTS:
        try:
            run_explore_loop(session, conn, MAX_CONCURRENT)
            window_start = time.time()  # a clean return counts as healthy
        except KeyboardInterrupt:
            elog.info("Shutting down (KeyboardInterrupt)")
            return 0
        except UnusableConnectionError as e:
            elog.error("Stopping explorer with unusable database connection: %s", e, exc_info=True)
            try:
                conn.close()
            except Exception:
                elog.exception("Failed to close unusable database connection")
            return 1
        except (Exception, SystemExit) as e:
            healthy_for = time.time() - window_start
            if healthy_for >= HEALTHY_RUN_SEC:
                elog.info("Ran healthy for %.0fs, resetting restart counter", healthy_for)
                restarts = 0
            restarts += 1
            elog.error("Crash #%d: %s", restarts, e, exc_info=True)
            log.error("Crash #%d: %s — restarting in %ds", restarts, e, RESTART_DELAY)
            window_start = time.time()
            try:
                time.sleep(RESTART_DELAY)
            except KeyboardInterrupt:
                elog.info("Shutting down during restart delay (KeyboardInterrupt)")
                return 0
            new_session = _session_or_none()
            if new_session is not None:
                session = new_session
                elog.info("Re-authenticated after crash #%d", restarts)
            else:
                elog.error("Re-auth failed after crash #%d; retrying with existing session", restarts)

    elog.error("Max restarts (%d) reached, exiting", MAX_RESTARTS)
    log.error("Max restarts (%d) reached, exiting", MAX_RESTARTS)
    return 1


if __name__ == "__main__":
    sys.exit(main())

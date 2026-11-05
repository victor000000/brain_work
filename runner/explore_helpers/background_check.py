"""Run check_new_alphas in a daemon thread so it doesn't block the loop."""

import threading

from checker.auto_check import check_new_alphas
from core.auth import get_session
from core.db import get_conn
from runner.explore_helpers._constants import elog

_check_thread = None


def _run_check_in_thread():
    """Thread target: its own DB connection and its own HTTP session.

    Both are per-thread resources, and sharing either is a real fault, not a
    style point. The thread already opened its own DB connection, because
    DuckDB is single-writer; it did not do the same for the session, so the
    main loop and the check thread used one `requests.Session` at the same
    time. That class is not thread-safe, and the corrupted connection pool
    showed up as HTTP 200 with an **empty body**: 44 of 66 previews inside a
    check run, against 0 of 10 when the same requests were fired from a
    single-threaded caller, and the same alphas answering in under a second.

    Each run costs one extra authentication POST. The alternative is every
    check paying a 45s stall for a response the platform had already sent.
    """
    try:
        thread_conn = get_conn()
        check_new_alphas(get_session(), thread_conn)
        thread_conn.close()
    except Exception as e:
        elog.warning("Background check error: %s", e)


def start_background_check():
    """Run check_new_alphas in a background thread so it doesn't block the loop."""
    global _check_thread
    if _check_thread and _check_thread.is_alive():
        elog.debug("Background check still running, skipping")
        return
    _check_thread = threading.Thread(target=_run_check_in_thread, daemon=True)
    _check_thread.start()
    elog.info("Started background alpha check")

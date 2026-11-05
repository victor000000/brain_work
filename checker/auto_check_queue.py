"""The auto-check queue: who is eligible, and how deferrals reorder it.

Split out of `checker/auto_check.py`, which re-exports these names.
"""

import time

from checker.auto_check_deferrals import _note_deferral  # noqa: F401
from checker.auto_check_rank import RERANK_WINDOW, by_expected_value
from core.log import get_file_logger
from generator.diversity_weights.compute_count import _REACHABLE_SQL as REACHABLE_SQL
from runner.submit.eligibility import build_eligibility_union

rlog = get_file_logger("runner")

# Statuses that must never re-enter the check queue.
TERMINAL_STATUSES = ("SUBMITTED", "REJECTED")

# Alphas per check run. Raised from 20 on 2026-10-05, when 49 eligible alphas
# sat unchecked — among them a sharpe-2.74 candidate — while the runs cleared
# 20 at a time, twice an hour, against a supply arriving faster than that. A
# check is a preview GET and costs no simulation budget, so an unchecked
# gate-passer is pure lost opportunity: it is exactly how the three accepted
# alphas were found. The run is a daemon thread and `start_background_check`
# skips while one is in flight, so a longer run cannot stack.
CHECK_BATCH_LIMIT = 60

# Wall-clock ceiling on one check run. Each alpha costs a preview GET (45s
# ceiling) plus up to two correlation polls (60s each), so a congested platform
# puts a 60-alpha run at close to three hours — and while it runs,
# `start_background_check` no-ops and no new alphas are checked at all. Seen
# 2026-10-06: a run started 08:27 with 43 alphas and was still going at 09:12.
# The summary is what drains the queue, so the alphas not reached simply come
# back on the next run; stopping early costs nothing but a turn.
CHECK_RUN_BUDGET_SEC = 1200

# An alpha whose preview never lands keeps no summary, so it stays eligible —
# and deferral *ordering* alone only sends it to the back of the queue, it does
# not keep it out of the run. Measured 2026-10-08: 32 distinct alphas produced
# 568 CHECK_UNAVAILABLE_GIVEUP lines, 30 of them with 5 or more (worst: 28),
# while a preview deadline is now 90s. That is why runs kept timing out on the
# same handful: ~30 chronic alphas can eat a whole CHECK_RUN_BUDGET_SEC run
# between them and starve every alpha behind them — and the alphas behind them
# are where the accepted ones come from.
#
# `attempts` was already recorded on every deferral and never read. This acts
# on it, as a cooldown rather than a blacklist: what blocks a preview is
# platform state (an account-wide quota) and that does change, so the alpha
# gets another look once the cooldown expires.
DEFERRAL_BACKOFF_AFTER = 3
DEFERRAL_BACKOFF_SEC = 6 * 3600


def _backoff_cutoff():
    """The `last_at` at which a deferral stops holding an alpha back.

    Formatted exactly as `_note_deferral` writes it: the column is TEXT and the
    comparison is lexicographic, so a differently shaped string would compare
    confidently and wrongly rather than raise.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - DEFERRAL_BACKOFF_SEC))


def _select_candidates(conn, limit):
    """The run's queue: eligible, unchecked alphas, deferred ones last.

    Selection mirrors the platform's must-pass thresholds via the shared
    build_eligibility_union() (per-region sharpe floors) instead of hardcoded
    ones, skips alphas that already reached a terminal status, and skips rows
    that already have a check summary so the queue drains.

    It also applies the pv/option reachability filter: submissions must stay
    inside the data scope, and the legacy corpus is full of alphas built on
    categories the project no longer uses (only ~8.6% of stored alphas are
    in scope).

    The summary test is NOT EXISTS rather than NOT IN. The hazard that
    motivated it — a nullable TEXT key under SQLite, where one NULL row makes
    `NOT IN` evaluate to NULL for every candidate and silently starves the
    queue — is now structurally impossible (DuckDB enforces the primary key as
    NOT NULL), but NOT EXISTS is the safer form and costs nothing.
    """
    rows = conn.execute(
        f"""
        SELECT alpha_results.alpha_id, alpha_results.is_sharpe, alpha_results.template,
               (check_deferrals.alpha_id IS NOT NULL) AS deferred,
               alpha_results.region, alpha_results.universe, alpha_results.delay
        FROM alpha_results
        LEFT JOIN check_deferrals ON check_deferrals.alpha_id = alpha_results.alpha_id
        WHERE {build_eligibility_union()}
          AND {REACHABLE_SQL}
          AND (status IS NULL OR status NOT IN (?, ?))
          AND NOT EXISTS (
              SELECT 1 FROM alpha_check_summary s WHERE s.alpha_id = alpha_results.alpha_id
          )
          -- Held back by the cooldown described above. COALESCE is
          -- load-bearing: `attempts` is NULL for every alpha that was never
          -- deferred, and `NOT (NULL >= 3 AND ...)` is NULL — which drops the
          -- row, silently emptying the queue of everything that works.
          AND NOT (
              COALESCE(check_deferrals.attempts, 0) >= ?
              AND check_deferrals.last_at > ?
          )
        -- An alpha whose check could not be decided keeps no summary, so it
        -- stays eligible; ordered by sharpe alone it would head every run and,
        -- now that a run is bounded by wall clock, starve everything below it.
        -- Deferred alphas sort last within the LIMIT — and, because the sort
        -- happens before the LIMIT, an undecided top-60 no longer fills the
        -- whole run. It comes back once nothing un-deferred is left.
        ORDER BY (check_deferrals.alpha_id IS NOT NULL), alpha_results.is_sharpe DESC
        LIMIT ?
    """,
        (*TERMINAL_STATUSES, DEFERRAL_BACKOFF_AFTER, _backoff_cutoff(), limit * RERANK_WINDOW),
    ).fetchall()

    return by_expected_value(rows, limit)

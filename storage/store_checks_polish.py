"""Queue a one-failure alpha for a settings-variant re-simulation.

Split out of `storage/store_checks.py`, which re-exports both names.
"""

from core.log import get_file_logger

clog = get_file_logger("check")

# An alpha this close to submission is worth re-running under other settings.
# The bound keeps a PASS/WARNING-heavy alpha with one odd failure out of the
# queue.
#
# A pending check does NOT disqualify a candidate. Requiring `pend_count == 0`
# looked prudent — a pending correlation can still resolve to a second failure —
# but the platform leaves something pending on almost every alpha
# (MATCHES_THEMES and POWER_POOL_CORRELATION sit PENDING routinely, and are
# permanent on the accepted alphas), so the condition rejected 100% of the
# recent one-failure alphas and starved the queue: polishing stopped for 100
# minutes on 2026-10-05 while every candidate that would have fed it was
# filtered out. The cost of being wrong is one polish attempt; the cost of the
# guard was the whole mechanism.
POLISH_MIN_PASSES = 10

# One-failure classes the queue no longer admits, because polishing them has
# never converted one — as amended twice in two days, and the second
# amendment is the one with a live test behind it.
#
# 2026-10-15: CONCENTRATED_WEIGHT left the set the day after it entered —
# the exclusion's 0-of-6 record had been taken under a settings axis that
# never carried a truncation below 0.05, and the corpus's DEU/TOP500
# report measures 0.01-0.02 as the zone that converts this check. An axis
# that was never tested cannot count against the class.
#
# 2026-10-16: the axis got its test — the first candidate it reached
# under t=0.02, decay 15, against its own t=0.1, decay 8 original. The
# CONCENTRATED_WEIGHT reading came back **0.234203 against 0.233743** —
# unchanged in the third decimal with the setting moved by a factor of
# five and the decay doubled. Whatever the check measures, truncation
# does not move it, which also explains the pre-wrap population (reads
# of 0.3-1.0 at every truncation 0.05/0.08/0.1). The class is excluded
# again, this time on a measurement rather than on a missing one.
#
# Measured 2026-10-14 on the parked-state backup, over every one-failure alpha
# in `alpha_check_summary` (the same population the enqueue condition admits):
# of the expressions whose single failure was one of these, **none ever
# produced a fully-clean alpha** — `LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO` 0 of
# 47, `LOW_ROBUST_UNIVERSE_SHARPE` 0 of 6, `CONCENTRATED_WEIGHT` 0 of 6 —
# against 30-50% for the classes beside them (`PROD_CORRELATION` 11 of 32,
# `LOW_2Y_SHARPE` 6 of 20, `IS_LADDER_SHARPE` 4 of 8, `LOW_SUB_UNIVERSE_SHARPE`
# 3 of 7). The zeroes read as structural rather than as luck: the queue varies
# the risk model or the decay/truncation pair, which rescales the PnL, but a
# sub-universe sharpe *ratio* comes from the expression's own cross-sectional
# structure, and it did not move under any axis the queue tried. The queue's
# own history agrees — all 100 candidates it ever admitted sit at the attempt
# cap, and these classes are 51 of them. Skipping the class at admission
# keeps the spend on the classes with a record. CONCENTRATED_WEIGHT's zero
# (0 of 6) shared this entry for a day and was wrong to: its working axis
# (truncation 0.01-0.02) simply was not in the pool — see the amendment
# above.
#
# The account-wide quota checks are deliberately absent: `store_checks`
# already refuses to summarize or enqueue those, and their "conversions" in
# the same measurement (`REGULAR_SUBMISSION` 5 of 7) are quota windows
# reopening, not polishing.
NON_CONVERTING_CHECKS = frozenset(
    {"LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO", "LOW_ROBUST_UNIVERSE_SHARPE", "CONCENTRATED_WEIGHT"}
)


def _enqueue_polish_candidate(conn, alpha_id, now):
    """Queue a one-failure alpha for a settings-variant re-simulation.

    A failure in `NON_CONVERTING_CHECKS` is not admitted at all: the queue's
    axes have never converted one of those classes, and four simulations
    per expression re-grew the same failure.

    The expression and cell come from `alpha_results`; an alpha with no stored
    row (a check run on something we did not simulate) is skipped rather than
    inserted with empty fields. `INSERT OR IGNORE` keeps the first sighting's
    `attempts` counter, so re-checking an alpha does not reset its budget.

    One row per *expression*, not per alpha. Polish re-simulates a candidate,
    the new alpha carries the same expression, and if it fails one check it
    comes straight back here — so without the guard the queue feeds itself: on
    2026-10-07 it held 191 candidates covering **22 expressions**, one of them
    75 times over. Every duplicate spends its own four re-runs producing a
    signal already simulated, and they then fail SELF_CORRELATION against each
    other, which is exactly what the twenty failures that morning were.

    Excluding an expression that has *retired* too is deliberate: four
    neutralizations that did not convert will not convert on a fifth.
    """
    failed = {
        r[0]
        for r in conn.execute(
            "SELECT check_name FROM submission_checks WHERE alpha_id = ? AND result = 'FAIL'",
            (alpha_id,),
        ).fetchall()
    }
    if failed and failed <= NON_CONVERTING_CHECKS:
        clog.info(
            "%s: only %s failed — no conversion record under polish, not queueing",
            alpha_id,
            sorted(failed),
        )
        return

    # `RETURNING` distinguishes a real enqueue from one the guard rejected. The
    # log line below used to fire unconditionally after this statement, so a
    # starved queue read as a fed one: five candidates on 2026-10-07 were
    # reported "queued for a settings-variant re-run" while every one of them
    # was excluded, their expressions already in the table.
    queued = conn.execute(
        """INSERT OR IGNORE INTO polish_candidates
               (alpha_id, expression, region, universe, delay, neutralization,
                attempts, created_at)
           SELECT alpha_id, expression, region, universe, delay, neutralization, 0, ?
           FROM alpha_results
           WHERE alpha_id = ? AND expression IS NOT NULL
             AND NOT EXISTS (
                 SELECT 1 FROM polish_candidates p WHERE p.expression = alpha_results.expression
             )
           RETURNING alpha_id""",
        (now, alpha_id),
    ).fetchall()
    if queued:
        clog.info("%s: one failing check — queued for a settings-variant re-run", alpha_id)
        return
    # Say which of the two reasons applied. The combined wording read the same
    # either way, and they mean opposite things: an expression already in the
    # queue is the anti-feed guard working (191 candidates once covered 22
    # expressions), while no stored row is a bug worth chasing. Observed
    # 2026-10-08 on `A1vVPZ9l` and `mL6obRR1`, queued seconds after a sibling
    # failing the same check — indistinguishable under the old message from two
    # alphas missing from `alpha_results`.
    row = conn.execute("SELECT expression FROM alpha_results WHERE alpha_id = ?", (alpha_id,)).fetchone()
    if row is None:
        clog.warning("%s: not queued — no alpha_results row for it", alpha_id)
    elif not row[0]:
        clog.warning("%s: not queued — its alpha_results row carries no expression", alpha_id)
    else:
        clog.info("%s: not queued — its expression already entered the polish queue", alpha_id)

"""Per-neutralization pass weights from the platform's own verdicts.

Split out of `runner/explore_helpers/polish.py`, which re-exports
`outcome_weights` — `take_batch` and the tests both reach for it there.
"""

from core.log import get_file_logger

plog = get_file_logger("submit")


def outcome_weights(conn) -> dict[str, float]:
    """Per-neutralization weight from the platform's own verdicts, smoothed.

    `(passed + 1) / (checked + 2)` — a Laplace-smoothed pass rate over every
    alpha that has a check summary, so a neutralization that has never been
    tried sits at 0.5 rather than 0, and one with a couple of passes earns a
    modest edge rather than a monopoly. An empty or unreadable table yields {}
    and the caller falls back to a uniform pick.

    Evidence for weighting at all: on 2026-10-05 `REVERSION_AND_MOMENTUM` was
    the only neutralization with more all-check passes than correlation
    failures (2 of 3 alphas passed everything, against 1 of 23 for the rest
    combined), and the earlier cross-day sample independently put it top. Two
    small samples agreeing is worth acting on, but only as a nudge — the
    expression is what correlates, not the neutralization.
    """
    try:
        rows = conn.execute(
            """SELECT a.neutralization, COUNT(*) AS n,
                      SUM(CASE WHEN s.fail_count = 0 THEN 1 ELSE 0 END) AS passed
               FROM alpha_results a JOIN alpha_check_summary s ON s.alpha_id = a.alpha_id
               WHERE a.neutralization IS NOT NULL
               GROUP BY 1"""
        ).fetchall()
    except Exception as e:  # table missing on an old DB: fall back to uniform
        plog.debug("outcome weights unavailable: %s", e)
        return {}
    return {name: (int(passed or 0) + 1) / (int(n) + 2) for name, n, passed in rows if n}

"""Per-template correlation penalty, measured from the latest stored checks.

`cell_priors.hit_weight` answers "how often does this shape's alphas reach the
sharpe floor?". It does not answer "and of those, how many can actually be
submitted?" — production and self correlation decide that, and they are the
binding gate. Of the 1,556 alphas ever checked, 119 carry a PROD_CORRELATION
failure and 54 a SELF_CORRELATION one, and the rate is wildly uneven by shape:
`quantile_ts_rank` failed production correlation on 36.7% of its checked alphas
while `ts_backfill_negmean` has never failed it in 169 — and holds the best
floor rate of any template (6.92%).

So the weight the allocator wants is a product:
`P(reach the floor) x P(not correlated | reached it)`. `hit_weight` supplies the
first factor and this module the second, as a multiplier in [FLOOR, 1.0].
Multiplier, never a block: a shape that fails correlation often can still be
the only one that passes it — `percentile_momentum` has one of the worst rates
in the table and produced the October acceptances — so this re-ranks rather
than retires, and "dont blacklist, dont block anything" holds.

A shape with no checks yet is left at 1.0 rather than penalised for being new.

Generation uses the matching (template, region, universe, delay) record.
A crowded HKG cell must not penalise an unmeasured EUR cell. Unknown cells
keep weight 1.0; measured cells retain the same smoothing and positive floor.
Callers without a cell retain the aggregate template weight for compatibility.
"""

import time

from core.log import get_file_logger
from core.time_sql import utc_timestamp_sql

glog = get_file_logger("generator")

# Beta(1, 9) prior on the correlation-failure rate — centred on 10%, near the
# base rate observed (119/1,556 = 7.6% for production), weak enough that a
# shape with 20 checked alphas and no failures still lands near zero.
_ALPHA, _BETA = 1.0, 9.0

# The multiplier never reaches zero: this re-ranks, it does not retire, and the
# "dont blacklist, dont block anything" constraint holds. It is 0.1 rather than
# the 0.5 first written here, because 0.5 was binding where the measurement was
# already decisive and so threw the evidence away. `sector_neutralized` failed
# correlation on **58 of 58** checked alphas today — a Beta(1,9) posterior puts
# it at 0.13, and even the 95% lower bound (78%) only reaches 0.22 — yet 0.5
# gave it a multiplier four times more generous than the data. Its 60 floor
# passers a day are all unsubmittable, and they cost simulations *and* check
# slots that the check-queue re-rank would otherwise give to shapes that convert.
FLOOR = 0.1

# How far back a check counts. A shape's correlation record is a statement about
# what it is producing now; `checked_at` is written in this exact format (see
# store_checks), so the comparison is like-for-like.
RECENT_WINDOW_SEC = 7 * 24 * 3600

_corr_weight: dict[str, float] = {}
_cell_corr_weight: dict[tuple[str, str, str, int], float] = {}

# Both arms block a submission, so both count as a failure here.
_CORR_CHECKS = ("PROD_CORRELATION", "SELF_CORRELATION")


def correlation_failure_rate(checked: int, failed: int) -> float:
    """Posterior mean of the failure rate, or 0.0 when nothing was checked."""
    if checked <= 0:
        return 0.0
    return (failed + _ALPHA) / (checked + _ALPHA + _BETA)


def load_corr_prior(conn) -> None:
    """Replace the cache with per-template multipliers from the check record.

    `alpha_check_summary` is the denominator, not `check_failures`: only an
    alpha that was actually checked can say anything about its shape's
    correlation rate, and a shape whose alphas mostly never reach the gate
    should not look clean because of it.

    Latest submission_checks supply failures; check_failures retains historical
    observations even after an alpha passes and must not define its current
    outcome. Recent summary timestamps are compared as UTC instants.

    **Recent checks only.** Counting every check ever made the weight lag the
    shape's actual behaviour, and it showed: `percentile_momentum` carried a
    0.586 multiplier from an all-time 44.9% failure rate while its alphas were
    failing correlation on 7.4% of checks *today* — and at a 37.8% floor rate
    it was the best-converting shape in the account, penalised hardest among
    the productive ones. Over the same window `sector_neutralized` failed on
    100% of its checked alphas and `vol_adjusted_signal` on 77%, which is what
    the multiplier is for. A shape that fixes itself should be forgiven.
    """
    global _corr_weight, _cell_corr_weight
    cutoff = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - RECENT_WINDOW_SEC))
    rows = conn.execute(
        f"""
        SELECT a.template, a.region, a.universe, a.delay,
               COUNT(DISTINCT a.alpha_id),
               COUNT(DISTINCT CASE WHEN f.check_name IN {_CORR_CHECKS} AND f.result = 'FAIL' THEN a.alpha_id END)
        FROM alpha_results a
        JOIN alpha_check_summary s ON s.alpha_id = a.alpha_id
        LEFT JOIN submission_checks f ON f.alpha_id = a.alpha_id
        WHERE a.template IS NOT NULL
          AND {utc_timestamp_sql("s.checked_at")} >= CAST(? AS TIMESTAMP)
        GROUP BY 1, 2, 3, 4
        """,
        (cutoff,),
    ).fetchall()
    totals: dict[str, tuple[int, int]] = {}
    _cell_corr_weight = {}
    for template, region, universe, delay, checked, failed in rows:
        _cell_corr_weight[(template, region, universe, delay)] = max(
            FLOOR, 1.0 - correlation_failure_rate(checked, failed)
        )
        n, f = totals.get(template, (0, 0))
        totals[template] = (n + checked, f + failed)
    _corr_weight = {
        template: max(FLOOR, 1.0 - correlation_failure_rate(checked, failed))
        for template, (checked, failed) in totals.items()
    }
    glog.debug("loaded %d template and %d cell correlation weights", len(_corr_weight), len(_cell_corr_weight))


def corr_weight(template: str, *, cell: tuple[str, str, int] | None = None) -> float:
    """Matching-cell multiplier, or aggregate when no cell is requested.

    An unmeasured cell stays neutral, even if this shape failed elsewhere.
    """
    if cell is not None:
        return _cell_corr_weight.get((template, *cell), 1.0)
    return _corr_weight.get(template, 1.0)

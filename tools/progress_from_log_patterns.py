"""Log-line patterns and gate thresholds for the from-log progress summary.

Split out of `tools/progress_from_log.py`, which re-exports them so the module
stays the single import path. The regexes are anchored to the exact line
formats the runner logs; the comments show the lines they match.
"""

import re

from runner.submit.eligibility import (
    MIN_FITNESS,
    MIN_SHARPE_DEFAULT,
    MIN_TEST_SHARPE,
    REGION_DELAY_MIN_SHARPE,
    REGION_MAX_TURNOVER,
    TURNOVER_MAX,
    TURNOVER_MIN,
)

# 2026-10-05 08:40:14,184 [INFO] log_alpha:58 alpha=X sh=0.43 ts=0.64 fi=0.09 \
#   to=0.2867 rn=0.00 USA/TOP500/d0 n=SLOW_AND_FAST
ALPHA_RE = re.compile(
    r"^(?P<ts>\S+ \S+) \[INFO\] log_alpha:\d+ alpha=(?P<id>\S+) "
    r"sh=(?P<sh>-?[\d.]+) ts=(?P<ts_>-?[\d.]+) fi=(?P<fi>-?[\d.]+) "
    r"to=(?P<to>-?[\d.]+) rn=(?P<rn>-?[\d.]+) "
    r"(?P<region>\w+)/(?P<uni>[^/]+)/d(?P<delay>\d+) n=(?P<neut>\S+)"
)

# 2026-10-05 08:39:16,006 [WARNING] store_checks:76 RR6dnVMb FAIL PROD_CORRELATION limit=0.7 val=0.7807
CHECK_RE = re.compile(
    r"\[WARNING\] (?:store_checks|_record_check_rows):\d+ "
    r"(?P<id>\S+) (?P<result>FAIL|PASS) (?P<check>\S+)"
)
# 2026-10-05 08:39:16,087 [INFO] store_checks:92 RR6dnVMb: P=13 F=2 W=5 Pend=0
# Only FAILs get a per-check line, so the pass/warning totals come from here.
CHECK_SUMMARY_RE = re.compile(
    r"store_checks:\d+ (?P<id>\S+): P=(?P<p>\d+) F=(?P<f>\d+) W=(?P<w>\d+) Pend=(?P<pend>\d+)"
)
TEMPLATE_RE = re.compile(r"record_template_performance:\d+ Template (?P<name>\S+) -> (?P<id>\S+)")
# 2026-10-05 09:36:21,831 [INFO] take_batch:109 B7: polishing 3 near-miss alpha(s)
#   in HKG/TOP800/d1 under NONE: 0mr9n8N6, 0mrdYeM6
# The batch index was added after the first batch ran, so it is optional: an
# older line still reports its candidates, it just cannot be joined to results.
POLISH_RE = re.compile(
    r"take_batch:\d+ (?:B(?P<idx>\d+): )?[Pp]olishing (?P<n>\d+) near-miss alpha\(s\) "
    r"in (?P<region>\w+)/(?P<uni>[^/]+)/d(?P<delay>\d+) under (?P<neut>\S+): (?P<ids>.+)$"
)
# 2026-10-05 01:22:01,972 [INFO] fetch_alpha:29 B4 alpha JjQnwOJx: sharpe=0.36 USA/TOP500
# 2026-10-09 01:43:33,941 [INFO] handle_single:40 B584 alpha omWawNWl: sharpe=0.09 KOR/TOP600
#
# Two loggers, one line shape: `fetch_alpha` writes it for each child of a
# multi-expression batch, `handle_single` for a batch whose alpha is on the
# parent. Matching only the first silently dropped every single-expression
# batch — i.e. every polish batch, since `take_batch` polishes one near-miss at
# a time — so `make progress` reported 20 of 24 polish batches "no results yet"
# hours after they had finished, and the polish path looked like it produced
# nothing when it had produced the day's acceptances.
#
# The sharpe group is optional because `handle_single` only grew its INFO line
# on 2026-10-09: before that its only matchable line was "B584 alpha
# omWawNWl: HTTP 200". `collect` fills the gap from alpha.log by alpha id.
BATCH_ALPHA_RE = re.compile(
    r"(?:fetch_alpha|handle_single):\d+ B(?P<idx>\d+) alpha (?P<id>\S+):"
    r"(?: sharpe=(?P<sh>-?[\d.]+))?"
)
ERROR_BATCH_RE = re.compile(r"done \(error\): (?P<msg>.+?) age=\d+s")

# Local eligibility gate. The thresholds are imported rather than restated:
# this file used to hold its own `{"CHN": 2.07}` beside a `1.58` default, which
# is the same knowledge `runner/submit/eligibility.py` owns and the same drift
# the posterior carried (it hard-coded 1.58 for every cell and credited CHN
# with 2.3x the eligibility it had). `SHARPE_FLOOR` stays as a region-keyed
# view for callers that have no delay; `passes_gate` prefers the exact
# (region, delay) entry.
SHARPE_FLOOR_DEFAULT = MIN_SHARPE_DEFAULT
SHARPE_FLOOR = {region: floor for (region, _delay), floor in REGION_DELAY_MIN_SHARPE.items()}
FITNESS_FLOOR = MIN_FITNESS
TURNOVER_BAND = (TURNOVER_MIN, TURNOVER_MAX)
# IND's ceiling is 0.4, not 0.7 (see runner/submit/eligibility.py).
TURNOVER_CEILING = dict(REGION_MAX_TURNOVER)
TEST_SHARPE_FLOOR = MIN_TEST_SHARPE
# `test_sharpe > MIN_TEST_SHARPE` in that same clause, which this gate mirrored
# without it. The gap is small — 0-3 alphas a day, ~7% on 2026-10-08 — but it is
# the flattering direction: it counts alphas the selector will never pick, and
# the clearest of them (0mrYmzEp, IS sharpe 8.29) has a test sharpe of 0.00.
TEST_SHARPE_FLOOR = 0

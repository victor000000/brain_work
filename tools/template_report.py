#!/usr/bin/env python3
"""Which templates earn their weight: per-shape results since a cutoff.

The registry's weighting spends budget on coverage and on each shape's record,
and the record is spread across tables nothing summarises per shape:
`alpha_results.template` labels every stored alpha, `check_failures` carries
which check blocks what (with the limit and the observed value), and
`simulations` carries `submitted_at`/`completed_at` — the first of which was
NULL for all 322,047 rows until 2026-10-12, so per-shape latency could not be
measured at all before that.

Built for the question this loop keeps asking and hand-writing SQL for. After a
batch of shapes ships, which of them produce alphas that reach their cell's
floor, which spend simulations on nothing, and what blocks the ones that get
close.

Reads a database directly, so it needs the live one to be free or a backup:
while the explorer runs, the live database is locked, and `--db` exists for
that (the backup is also the only way to see *vintage* results).

Usage:
    python3 tools/template_report.py                              # 48h, all templates
    python3 tools/template_report.py --since 2026-10-12 --top 20
    python3 tools/template_report.py --template ts_ir_trend --since 2026-10-12
"""

import argparse
import calendar
import math
import os
import statistics
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.time_sql import utc_timestamp_sql  # noqa: E402
from runner.submit.eligibility import REGION_DELAY_MIN_SHARPE  # noqa: E402
from tools.report_db import open_report_db  # noqa: E402

DEFAULT_FLOOR = 1.58
_TS = "%Y-%m-%d %H:%M:%S UTC"


def floor_for(region, delay):
    """The sharpe this cell's alphas must reach to be submittable."""
    return REGION_DELAY_MIN_SHARPE.get((region, delay), DEFAULT_FLOOR)


def duration_seconds(submitted_at, completed_at):
    """Seconds between two `… UTC` stamps, or None when either is missing/bad.

    Every timestamp here is the project's own text format (`store_sim.utc_text`),
    so a parse failure means a NULL, not a format to guess at.
    """
    if not submitted_at or not completed_at:
        return None
    try:
        start = calendar.timegm(time.strptime(submitted_at, _TS))
        end = calendar.timegm(time.strptime(completed_at, _TS))
    except ValueError:
        return None
    return end - start


def summarize(alphas, latencies=(), failures=()):
    """Aggregate `(template, region, delay, sharpe)` rows into per-template rows.

    `latencies` is `(template, seconds)` and `failures` is `(template,
    check_name)`, both already filtered to the window. Pure, so the report can
    be tested without a database.
    """
    acc = {}
    for template, region, delay, sharpe in alphas:
        row = acc.setdefault(
            template,
            {"alphas": 0, "sharpes": [], "at_floor": 0, "latencies": [], "failures": {}},
        )
        row["alphas"] += 1
        if sharpe is not None and math.isfinite(sharpe):
            row["sharpes"].append(sharpe)
            if sharpe >= floor_for(region, delay):
                row["at_floor"] += 1
    for template, seconds in latencies:
        if template in acc and seconds is not None:
            acc[template]["latencies"].append(seconds)
    for template, check_name in failures:
        if template in acc:
            row = acc[template]["failures"]
            row[check_name] = row.get(check_name, 0) + 1
    return acc


def _median(values):
    return statistics.median(values) if values else None


def format_row(template, row):
    sharpes = sorted(row["sharpes"])
    med = _median(sharpes)
    best = sharpes[-1] if sharpes else None
    lat = _median(row["latencies"])
    top_fail = max(row["failures"].items(), key=lambda kv: kv[1])[0] if row["failures"] else ""
    return (
        f"{template:<28} {row['alphas']:>6} {('' if med is None else f'{med:+.3f}'):>7} "
        f"{('' if best is None else f'{best:+.2f}'):>6} {row['at_floor']:>5} "
        f"{(100 * row['at_floor'] / row['alphas'] if row['alphas'] else 0):>5.1f}% "
        f"{('' if lat is None else f'{lat:.0f}s'):>6} {top_fail:<32}"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default=None, help="UTC date or 'YYYY-MM-DD HH:MM:SS' (default: 48h ago)")
    ap.add_argument("--db", default=os.path.join(PROJECT_DIR, "brain_data.duckdb"), help="database to read")
    ap.add_argument("--template", default=None, help="one template label (substring)")
    ap.add_argument("--top", type=int, default=0, help="show only the N busiest templates (0 = all)")
    args = ap.parse_args()

    since = args.since or time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 48 * 3600))
    if len(since) == 10:
        since += " 00:00:00"

    conn, args.db = open_report_db(args.db)
    try:
        return report(conn, args, since)
    finally:
        conn.close()


def report(conn, args, since):
    where = f"WHERE {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP)"
    params = [since]
    if args.template:
        where += " AND template LIKE ?"
        params.append(f"%{args.template}%")
    alphas = conn.execute(
        f"SELECT template, region, delay, is_sharpe FROM alpha_results {where} AND template IS NOT NULL",
        params,
    ).fetchall()

    latencies = []
    try:
        latencies = conn.execute(
            "SELECT a.template, s.submitted_at, s.completed_at FROM alpha_results a "
            "JOIN simulations s ON a.alpha_id = s.alpha_id "
            "WHERE s.completed_at >= ? AND s.submitted_at IS NOT NULL",
            [since],
        ).fetchall()
        latencies = [(t, duration_seconds(sub, comp)) for t, sub, comp in latencies]
    except Exception as e:  # a vintage without the join paths is still worth reporting
        print(f"(latency unavailable: {str(e)[:80]})")

    failures = []
    try:
        failures = conn.execute(
            "SELECT a.template, f.check_name FROM check_failures f "
            "JOIN alpha_results a ON a.alpha_id = f.alpha_id "
            f"WHERE {utc_timestamp_sql('a.created_at')} >= CAST(? AS TIMESTAMP)",
            [since],
        ).fetchall()
    except Exception as e:
        print(f"(check failures unavailable in this database: {str(e)[:60]})")

    if args.template:
        latencies = [(t, s) for t, s in latencies if args.template in (t or "")]
        failures = [(t, c) for t, c in failures if args.template in (t or "")]

    acc = summarize(alphas, latencies, failures)
    if not acc:
        print(f"no labelled alphas since {since} in {os.path.basename(args.db)}")
        return 1

    rows = sorted(acc.items(), key=lambda kv: -kv[1]["alphas"])
    if args.top:
        rows = rows[: args.top]
    print(f"db: {os.path.basename(args.db)}   since {since}   templates: {len(acc)}")
    print(
        f"{'template':<28} {'alphas':>6} {'med sh':>7} {'best':>6} {'floor':>5} {'rate':>6} {'med lat':>6} "
        f"{'top failing check':<32}"
    )
    for template, row in rows:
        print(format_row(template, row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
